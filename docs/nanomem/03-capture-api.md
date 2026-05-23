# Capture API

Status: v1 freeze candidate

This document defines the current capture API contract.

## 1. Purpose

`capture` receives a user-visible dialogue and appends extracted personal
MemoryUnits when appropriate.

Capture is not a generic event log, document ingestion API, workspace archive
API, or multimodal asset ingestion API.

## 2. Request Shape

```python
CaptureRequest:
  scope: MemoryScope
  dialogue: CaptureDialogue
  capture_time: str
```

```python
MemoryScope:
  owner_id: str
  namespace: str | None
```

```python
CaptureDialogue:
  messages: tuple[DialogueMessage, ...]
  occurred_at: str
  metadata: dict
```

```python
DialogueMessage:
  role: str
  content: str
  timestamp: str
  speaker_id: str | None
  metadata: dict
```

## 3. Core Invariants

Capture has these first-version invariants:

- `capture_time`, `dialogue.occurred_at`, and every message `timestamp` are
  required ISO 8601 timestamps with timezone.
- `dialogue.messages` must contain at least one non-empty user-visible message.
- `metadata` is caller-defined JSON and must not replace core fields.
- Capture inputs describe what happened, not how extraction should chunk or
  process the dialogue. Algorithm parameters belong to extractor configuration,
  not `CaptureDialogue` or `CaptureRequest`.
- message `role` should describe a visible dialogue function. Hidden messages,
  tool calls, tool results, and raw outputs are skipped by extraction and should
  not be sent as ordinary capture evidence.
- Capture archives a `DialogueRecord` before extraction.
- Every accepted MemoryUnit has `scope`, `text`, `memory_type`, `timestamp`,
  `available_at`, lifecycle fields, and at least one `DialogueRef`.
- Every accepted MemoryUnit has a resolved, validated, non-null namespace.
- `available_at` is the time NanoMem accepted the unit, normally
  `capture_time`.
- Capture is append-only. It does not replace old facts, resolve conflicts, or
  synthesize a canonical profile.
- Hidden reasoning, tool calls, tool results, raw files, and raw multimodal
  assets must not become MemoryUnits.

## 4. Namespace Semantics

Capture writes to exactly one namespace per MemoryUnit.

Rules:

- `scope.owner_id` is required.
- `scope.namespace` omitted means the request is resolved to
  `default_namespace` before storage.
- `scope.namespace` provided must be in `allowed_namespaces`.
- extractors must not invent namespaces.
- flexible tags belong in `MemoryUnit.metadata`, not `namespace`.

For multi-speaker capture, the host should provide stable `speaker_id` values.
Extraction may use them for attribution, but each accepted MemoryUnit still
lands in the request owner and one resolved namespace unless a future
multi-owner capture API is introduced.

## 5. CaptureDialogue

`CaptureDialogue` is the dialogue payload supplied by the host agent for one
capture call. It is normalized and archived as a control-plane
`DialogueRecord` before extraction; it is not itself a stored memory object.

It is not a session, conversation, turn, or transcript. NanoMem does not model
session lifecycle. Concurrent sessions and long-running sessions are represented
as multiple independent capture calls for the same `owner_id`.

```python
CaptureDialogue:
  messages: tuple[DialogueMessage, ...]
  occurred_at: str
  metadata: dict
```

Allowed dialogue messages:

- user messages;
- explicit preferences;
- user corrections;
- durable decisions;
- user-visible assistant final replies;
- multi-speaker dialogue segments with stable `speaker_id` values.

Disallowed capture material:

- hidden reasoning;
- tool calls;
- raw tool results;
- full logs;
- current task progress;
- raw files or raw multimodal assets;
- complete chat archives.

Current extractor behavior treats roles outside `user`, `assistant`,
`system_visible`, and `other` as non-extractable and returns skip reasons rather
than storing memory units.

External resources are consumed by the agent or tools before capture. If their
content matters, it should appear in user-visible dialogue, such as a user
message, assistant final answer, or visible summary. NanoMem captures from that
dialogue-level evidence.

Host session ids, turn ids, run ids, log pointers, and window counters are
optional host metadata. Put them in `metadata` only when useful for audit. They
must not become required NanoMem fields.

For long-running or multi-day sessions, the host should call capture repeatedly
with bounded new messages. It should not replay the entire session transcript on
every capture.

`metadata` is caller-defined JSON metadata. It can carry adapter-specific
fields, experiment labels, project hints, UI context, audit hints, or host log
references. It should not replace core fields such as owner, namespace,
timestamp, or dialogue content.

Time is required in the core capture contract. `capture_time`,
`dialogue.occurred_at`, and each message `timestamp` must be resolved before
extraction. If exact per-message time is unavailable, the host may set message
timestamps to `dialogue.occurred_at`; if the dialogue time is unknown, use
`capture_time`.

## 6. Replay Safety

First-version capture does not include idempotency in the core API. A replayed
capture may append duplicate MemoryUnits. Hosts that need retry safety can avoid
replaying completed captures or perform their own request deduplication.

Capture idempotency can be added later as a capture-boundary extension keyed by
owner, namespace, and a host-provided request key. It must not affect
MemoryUnit, DialogueRecord, read, ranking, or render semantics.

## 7. Extraction Style

Capture should produce third-person, evidence-grounded MemoryUnits.

Preferred:

```text
The user said they prefer concise Chinese answers.
The user asked the agent not to auto-commit code.
The agent auto-committed code and the user reacted negatively.
```

Avoid:

```text
I prefer concise Chinese answers.
Do not auto-commit code.
```

## 8. Pipeline

```text
CaptureRequest
  -> validate owner and namespace
  -> archive DialogueRecord
  -> normalize messages
  -> chunk = n over the message list
  -> annotate role and speaker_id
  -> extract personal facts
  -> attach DialogueRefs
  -> classify memory type
  -> apply quality gates
  -> append MemoryUnits
  -> update derived index
  -> record operation log
```

## 9. Response Shape

```python
CaptureResult:
  dialogue_id: str
  accepted_message_count: int
  unit_count: int
  units: tuple[MemoryUnit, ...]
  skipped: tuple[CaptureSkip, ...]
  stats: dict
  trace_ref: str | None
```

```python
CaptureSkip:
  message_range: tuple[int, int] | None
  reason: str
  detail: str | None
```

Skip reasons should be explicit enough for operators to distinguish:

- non-personal content;
- workspace-local content;
- duplicate dialogue;
- hidden/tool event;
- empty extraction;
- invalid namespace.
