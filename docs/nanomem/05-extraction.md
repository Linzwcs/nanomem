# Extraction

Status: draft

This document defines how NanoMem turns user-visible dialogue into durable
personal MemoryUnits.

## 1. Purpose

Extraction is responsible for finding long-term personal facts in a
`CaptureDialogue`. It is not a summarizer, document ingester, profile writer,
or truth-maintenance system.

Production extraction output should be fine-grained, third-person, timestamped,
scoped, and grounded in `DialogueRef`s. The LLM prompt/schema is responsible for
that wording. The heuristic extractor is a deterministic smoke-test baseline and
should stay simple rather than performing complex text rewriting.

## 2. Inputs And Outputs

```python
ExtractionRequest:
  scope: MemoryScope
  dialogue: DialogueRecord
```

```python
ExtractionResult:
  units: tuple[MemoryUnit, ...]
  skipped: tuple[ExtractionSkip, ...]
  stats: dict
```

`DialogueRecord` is already archived before extraction. Extractors read it as
evidence, but they must not expose raw dialogue through agent-facing read.
The record represents one capture payload, not a whole host session.

## 3. Pipeline

```text
DialogueRecord
  -> prepare visible messages
  -> chunk = n over visible dialogue text
  -> annotate role and speaker_id
  -> extract candidate personal facts
  -> convert to third-person MemoryUnit text
  -> assign owner and namespace
  -> assign timestamp and DialogueRef
  -> classify memory_type
  -> apply quality gates
  -> return units and skip reasons
```

`chunk = n` is an extraction window, not a storage unit. Chunk sizing is an
extractor configuration or implementation policy; it must not appear in
`CaptureDialogue` or per-request capture payloads. Implementations may choose
the tokenizer and windowing strategy, but should record enough stats to compare
quality and cost.

Chunking is internal to extraction. LLM-backed extraction should build chunks
from visible extractable messages, preserve original message indexes, split at
hidden/tool gaps, and prefer role-aware dialogue exchange boundaries. It does
not create session, turn, or conversation objects in the data model.

## 4. What To Extract

Extract durable user-related facts:

- stable preferences and communication style;
- user corrections to agent behavior;
- repeated habits and workflows;
- user background and relationship facts;
- important user events or decisions;
- user-visible agent actions that affect future collaboration.

Examples:

```text
The user said they prefer concise Chinese answers.
The user asked the agent not to auto-commit code.
The user decided NanoMem should store fact-level personal memory.
The agent auto-committed code and the user reacted negatively.
```

## 5. What To Skip

Skip:

- workspace-local facts that the agent can reread from files or tools;
- raw tool calls, tool results, hidden reasoning, and intermediate plans;
- current task progress with no long-term user relevance;
- raw external resources or asset references;
- vague, unsupported, or duplicate candidate facts;
- facts that cannot be assigned an owner, timestamp, and DialogueRef.

Skipping is expected behavior. A narrow memory system should skip more than it
stores.

## 6. Speaker And Scope

Extraction must preserve who said, asked, decided, corrected, or experienced a
fact.

Default capture writes units under `CaptureRequest.scope`. `speaker_id` is
evidence metadata for attribution, not a replacement for the request owner. If
a candidate cannot be clearly attributed to the requested owner, another named
speaker, or an agent interaction that matters to the owner, extraction should
skip it.

Extractors must not invent namespaces. If a namespace is omitted, capture policy
resolves it to the configured default before storage. Accepted units must carry
a non-null namespace.

## 7. Time Assignment

Every MemoryUnit needs `timestamp` and `available_at`.

- `timestamp` is the evidence time for the fact.
- If a fact comes from one message, use that message timestamp.
- If a fact spans multiple messages, use the latest message timestamp in the
  `DialogueRef.message_range`.
- If exact message time is unavailable, use `DialogueRecord.occurred_at`.
- `available_at` is assigned by capture when the unit is accepted.

All timestamps must be ISO 8601 with timezone.

## 8. Quality Gates

A candidate becomes a MemoryUnit only if it satisfies all gates:

- personal and durable;
- grounded in visible dialogue;
- third-person and evidence phrased;
- not an instruction masquerading as memory;
- not workspace-local source-of-truth content;
- owner and namespace resolved;
- `memory_type` is in the first-version allowed set;
- timestamp assigned;
- at least one `DialogueRef`;
- no redacted dialogue evidence is referenced;
- confidence above configured threshold, if a threshold is enabled.

Quality gates should return explicit skip reasons for inspection and tuning.

## 9. LLM Extractor Contract

Model-backed extraction is allowed, but the storage contract stays local and
deterministic:

- send only extractable visible messages to the model;
- keep original dialogue message indexes in the prompt payload;
- call the model per internal extraction chunk;
- require every accepted unit to return a valid `message_range`;
- reject ranges that cross hidden, tool, empty, or otherwise skipped messages;
- reject ranges outside the current chunk;
- classify `memory_type` using the first-version allowed set;
- treat low confidence as a skip when `confidence_threshold` is configured;
- use fallback extraction when provider calls or strict schema validation fail.

Capture revalidates extractor output before storage. This keeps custom
extractors from writing units with the wrong scope, invalid confidence, missing
timestamps, or unsafe dialogue references.

## 10. Deduplication

First-version capture does not provide request idempotency. Extraction may
suppress exact duplicates from the same dialogue, but it should not perform
semantic truth-maintenance deduplication.

Do not automatically replace:

```text
The user said they prefer pip.
The user later said this project should use uv.
```

Both can be useful evidence. Read and render should preserve time and context so
the downstream agent can reason.

## 11. Evaluation Harness

Extraction quality should be regression-tested before wiring real model
providers into capture. The eval harness compares an extractor against
deterministic cases:

- input `ExtractionRequest` dialogue;
- expected unit type, evidence range, text fragments, and minimum confidence;
- expected skip reason and optional message range;
- per-case pass/fail details and aggregate pass count.

Eval fixtures should avoid network calls. Fake LLM clients can test prompt
parsing and schema behavior, while the same cases can later run against a real
provider in offline quality checks.
