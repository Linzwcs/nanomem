# Behavior Cases

Status: draft

This document describes expected NanoMem behavior in concrete product cases.
It is not an API contract; it explains the design choices behind the core
capture, read, storage, and rendering rules.

## 1. Concurrent Sessions

Example:

```text
The same user has two agent sessions open for the same workspace.
Both sessions capture memories within the same hour.
```

Expected behavior:

- accept each `capture` request independently;
- use `owner_id`, namespace, and timestamps to separate writes;
- archive each dialogue before extraction;
- store extracted MemoryUnits as append-only evidence;
- avoid session-level locks unless the store backend requires transactional
  writes.

Why:

- NanoMem does not model session lifecycle.
- Concurrent sessions are normal host behavior, not a special memory mode.
- Append-only units make ordering and conflict handling explicit at read time.

## 2. Long-Running Or Multi-Day Sessions

Example:

```text
A coding agent runs over several days and periodically captures bounded
conversation windows.
```

Expected behavior:

- capture multiple bounded dialogues instead of one unbounded transcript;
- preserve source dialogue refs and timestamps for each extracted unit;
- let read requests use `query_time` for recency ranking and explicit
  `time_range` when strict bounds are needed;
- avoid relying on a session start or end event.

Why:

- bounded capture keeps extraction deterministic and cheap;
- timestamps provide the durable ordering signal;
- multi-day work should degrade into ordinary repeated capture calls.

## 3. User Preference Correction

Example:

```text
Earlier: The user prefers detailed explanations.
Later: The user says concise answers are better for routine updates.
```

Expected behavior:

- store the later preference as a new MemoryUnit;
- do not rewrite the older unit during normal capture;
- rank the newer correction higher when the query is about current style;
- render both facts when the correction context is useful and budget allows.

Why:

- preferences change over time;
- overwriting hides useful history and makes debugging harder;
- ranking and rendering can express "current" behavior without pretending the
  older memory never existed.

## 4. Conflicting Memories

Example:

```text
One memory says the user wants SQLite for local storage.
Another says the user wants Postgres for managed deployment.
```

Expected behavior:

- keep both MemoryUnits unless an explicit admin redaction or delete applies;
- rank conflict-relevant units together when the query needs the distinction;
- preserve timestamps and namespaces in rendered output;
- avoid automatic truth maintenance in the extractor.

Why:

- apparent conflicts often reflect scope, time, or environment differences;
- the store is authoritative evidence, not a single canonical profile;
- downstream agents need enough context to ask or choose safely.

## 5. Workspace-Local Facts

Example:

```text
The user says this repository has no pyproject.toml.
```

Expected behavior:

- skip the fact by default because the agent can reread the workspace;
- capture only if the dialogue promotes it to a durable user-relevant memory,
  such as a cross-project preference or correction;
- store any project or workspace hint in metadata, not as a namespace invented
  by the extractor;
- prefer live workspace inspection for volatile file state.

Why:

- local facts can become wrong outside the workspace;
- default reads search all allowed namespaces, so namespaces are not a safe
  place to hide volatile project state;
- NanoMem should not compete with the workspace as source of truth.

## 6. External Or Multimodal Resources

Example:

```text
The dialogue references an image, PDF, webpage, audio file, or raw dataset.
```

Expected behavior:

- do not store raw external resources as MemoryUnits;
- capture only durable, user-relevant claims that appear in user-visible
  dialogue;
- keep host resource pointers, if needed, only as non-evidence audit hints in
  `DialogueRecord.metadata`;
- do not put external resource refs in MemoryUnit evidence;
- avoid requiring NanoMem core to fetch, parse, OCR, or transcribe resources.

Why:

- external resource handling has security, privacy, cost, and freshness risks;
- NanoMem should remember facts, not become a document store;
- specialized host tools can extract resource summaries before capture.

## 7. Replay Without Idempotency

Example:

```text
A host retries capture after a timeout.
```

Expected behavior:

- first-version NanoMem may append duplicate MemoryUnits if the host replays a
  completed capture;
- hooks or wrappers should avoid replaying completed capture calls;
- later idempotency can be added as a capture-boundary extension without
  changing MemoryUnit or read semantics.

Why:

- replay safety is useful but not part of the core memory model;
- keeping it out of v1 keeps capture simple while the object model stabilizes;
- duplicate memories can be handled by later cleanup or deduplication tools.

## 8. Deletion And Redaction

Example:

```text
The user asks to remove a sensitive personal fact from memory.
```

Expected behavior:

- perform delete/redact through an admin/control-plane operation;
- remove or redact affected MemoryUnits from the authoritative store;
- delete corresponding derived index entries;
- record an operation log without preserving the sensitive text unnecessarily;
- avoid exposing delete/redact as a normal agent-facing read or capture tool.

Why:

- privacy operations require deliberate authority and audit behavior;
- indexes are derived and must follow the store;
- normal agent tools should not gain broad destructive capability.

## 9. Read Rendering Under Budget

Example:

```text
The read request has a 600-token context budget and 40 relevant candidate
memories.
```

Expected behavior:

- rank more candidates than can be rendered;
- render compact one-line MemoryUnits with mandatory timestamps;
- drop optional labels before dropping relevant facts;
- keep conflicts visible when relevant and budget allows;
- return structured ranked units separately for trusted host code.

Why:

- the final prompt text is the real budget surface;
- compact rendering improves fact coverage;
- structured results and prompt text serve different consumers.

## 10. Multi-Speaker Capture

Example:

```text
A meeting transcript includes the user, another human, and an assistant.
```

Expected behavior:

- preserve `role` and `speaker_id` in the archived DialogueRecord;
- extract user-specific memories only when attribution is clear;
- avoid treating another speaker's preference as the owner's preference;
- allow third-party facts only when scoped and useful to the owner;
- skip ambiguous claims with an explicit skip reason.

Why:

- memory quality depends on attribution;
- wrong-speaker extraction is worse than missing a marginal fact;
- archived dialogue refs let future inspection explain why a unit was created.
