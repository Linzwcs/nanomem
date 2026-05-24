# Memory Model

Status: draft

This document defines the conceptual data model for NanoMem. It is not limited
to the current implementation.

## 1. Layered Model

NanoMem separates archived dialogue evidence, durable memory, retrieval
candidates, and rendered context.

```text
DialogueRecord -> archived user-visible evidence
MemoryUnit     -> durable personal fact
IndexHit       -> derived retrieval candidate
RankedUnit     -> ordered evidence
PackedContext  -> rendered prompt evidence
```

The store is authoritative for MemoryUnits. Indexes are derived data and must
be rebuildable.

## 2. Core Invariants

These rules are part of the first-version contract:

- Time is mandatory and first-class. All timestamps use ISO 8601 with timezone,
  for example `2026-05-19T13:45:00+08:00` or `2026-05-19T05:45:00Z`.
- `metadata` is host-defined JSON. It must be JSON-serializable and must not
  override core fields such as owner, namespace, timestamp, dialogue content,
  or retention state.
- `metadata` is not automatically indexed or filterable. If a deployment needs
  fast metadata filters, it must explicitly copy selected keys into index
  filter fields.
- IDs are stable strings. NanoMem may generate `unit_id` and `dialogue_id`; a
  host may provide them only when it can guarantee uniqueness.
- Capture and read requests may omit namespace, but persisted MemoryUnits must
  carry a resolved, validated, non-null namespace.
- Capture archives a `DialogueRecord` before extraction. Without `session_id`,
  the request is treated as one complete dialogue and may be extracted
  immediately. With `session_id`, capture appends to the session's open
  dialogue window until it is sealed by token limit or explicit flush.
- `DialogueRef.message_range` is a message-index range, not a token, byte, or
  character range. It uses half-open `[start, end)` semantics.
- DialogueRecord message indices are immutable. Redaction must preserve index
  stability by tombstoning or replacing message slots rather than renumbering.
- Dialogue evidence is control-plane data. Agent-facing read returns
  MemoryUnits and rendered context, not raw DialogueRecords.
- Rendered context must show time for every MemoryUnit. Other display metadata
  is renderer-configurable.

## 3. MemoryScope

`MemoryScope` identifies whose memory is being accessed and which stable memory
space is used.

```python
MemoryScope:
  owner_id: str
  namespace: str | None
```

Scope semantics:

- `owner_id` is required. It identifies the person or named speaker who owns
  the memory.
- `namespace` is optional. It is a user- or host-defined stable memory category,
  not a free-form tag. Optional only applies to request input; stored
  MemoryUnits always use the resolved namespace.

`namespace` examples:

```text
personal
work
research
family
```

Avoid using temporary values as namespaces:

```text
session-123
task-456
ci-run-789
repo-nanomem
```

Project, agent, and tool references belong in metadata. `session_id` is a core
capture-routing field because it decides which visible messages should be
buffered together before extraction.

## 4. Namespace Rules

Namespaces are stable categories preconfigured by the user or host application.
Extractors must not invent namespaces.

Recommended configuration shape:

```yaml
scope:
  default_namespace: personal
  allowed_namespaces:
    - personal
    - work
    - research
```

Capture writes to exactly one namespace:

```text
capture.scope.owner_id = required
capture.scope.namespace omitted -> default_namespace
capture.scope.namespace provided -> must be in allowed_namespaces
```

Read may query one or more namespaces:

```text
read.owner_id = required
read.namespaces omitted -> all allowed namespaces for that owner
read.namespaces provided -> exactly those allowed namespaces
```

Default read should search all allowed namespaces because users usually expect
their personal memory to be found without knowing which stable category contains
it. Namespace filtering remains available when a caller wants a narrower memory
space.

Flexible labels should be stored as tags or metadata, not namespace:

```python
MemoryUnit.metadata = {
  "tags": ["engineering", "workflow"],
  "agent_ref": "codex",
  "project_ref": "nanomem"
}
```

## 5. DialogueRef

`DialogueRef` points back to user-visible dialogue evidence without making that
dialogue available to normal agent reads.

```python
DialogueRef:
  dialogue_id: str
  message_range: tuple[int, int] | None
```

`message_range` is a half-open range `[start, end)` over the archived message
list. `None` means the whole dialogue. First-version refs should avoid
`turn_id`, `message_index`, `role`, `char_range`, and arbitrary ref metadata;
those values are either derivable from the archived dialogue or too dependent
on the host agent harness.

Dialogue evidence is control-plane data:

```text
not indexed
not rendered
not exposed through agent tools
used only for audit, debugging, deletion, and re-extraction
```

External resources such as files, PDFs, images, browser pages, CRM records, and
tool results are not first-class NanoMem evidence. The agent or tool should
consume them, and only user-visible dialogue should be archived for reference.

## 6. DialogueRecord

`DialogueRecord` is control-plane evidence. It stores one user-visible dialogue
window as a structured message list so operators can audit, debug, delete, or
re-extract memories.

`DialogueRecord` carries `scope` and `session_id` because capture needs a
durable way to find the open dialogue window for an owner and namespace. It is
still not agent-facing memory: normal read never returns raw DialogueRecords.

```python
DialogueMessage:
  role: str
  content: str
  speaker_id: str | None
  timestamp: str
```

`role` is the visible dialogue function, such as `user`, `assistant`,
`system_visible`, or `other`. Hidden system/developer messages, tool events,
and raw tool results are not valid capture messages. `speaker_id` is a stable
actor id for the person or agent that produced the message; display names
belong in metadata if needed. An agent is a valid speaker.

```python
DialogueRecord:
  dialogue_id: str
  scope: MemoryScope
  session_id: str | None
  messages: tuple[DialogueMessage, ...]
  status: "open" | "sealed" | "extracted" | "failed"
  started_at: str
  ended_at: str
  created_at: str
  updated_at: str
  token_count: int
  checksum: str | None
  metadata: dict
  extracted_at: str | None
  retention_until: str | None
  redacted_at: str | None
```

`metadata` is host-defined JSON metadata. It may contain project, agent, UI,
experiment, adapter fields, or host log references, but NanoMem must not
require any metadata key for core semantics.

Every message has its own `timestamp`. Dialogue-level times describe the
window lifecycle: `started_at`, `ended_at`, `created_at`, `updated_at`, and
`extracted_at`.

DialogueRecords:

- are not indexed;
- are not returned by normal `read`;
- are not rendered into prompts;
- are not exposed through agent-facing MCP tools;
- have retention separate from MemoryUnits.

First local storage can keep DialogueRecords in SQLite alongside MemoryUnits,
but in separate tables and separate access paths.

## 7. Dialogue Capture Source

Capture source material is `CaptureDialogue`: a message list visible to the
user and agent. It is the request payload for capture, not a storage object. It
is not a raw tool log, document ingestion stream, or multimodal asset archive.
It is not a full conversation history. Host sessions may be long-running or
concurrent; NanoMem receives bounded capture payloads and appends them to an
open DialogueRecord only when the request includes `session_id`.

```python
CaptureDialogue:
  messages: tuple[DialogueMessage, ...]
  occurred_at: str
  metadata: dict
```

Capture without `session_id` turns `CaptureDialogue` into a sealed
`DialogueRecord` and extracts MemoryUnits immediately. Capture with
`session_id` appends the messages to that session's open DialogueRecord; flush
or token-limit sealing then extracts MemoryUnits whose `dialogue_refs` point
back to that record.

If the host needs buffered extraction, it must provide `session_id` on the
capture request. Other host identifiers such as conversation id, turn id, run
id, and external log pointers stay in metadata.

Allowed source messages include user messages, user corrections, explicit
preferences, durable decisions, user-visible assistant final replies, and
multi-speaker dialogue segments with stable `speaker_id` values.

Disallowed source material includes hidden reasoning, tool calls, raw tool
results, full logs, raw files, raw multimodal assets, and intermediate planning.

## 8. MemoryUnit

`MemoryUnit` is the durable storage unit.

```python
MemoryUnit:
  unit_id: str
  scope: MemoryScope
  text: str
  memory_type: str
  timestamp: str
  available_at: str
  dialogue_refs: tuple[DialogueRef, ...]
  retention_until: str | None
  redacted_at: str | None
  metadata: dict
```

The primary payload is `text`. `timestamp` is the evidence time for the fact.
When the exact fact time is not known, use the referenced dialogue time.
`available_at` is when NanoMem stored it. Structured
annotations such as subject/predicate/object, polarity, speaker attribution, and
source time ranges can be added later, but they are not first-version core
fields and should not imply canonical truth maintenance. `retention_until` and
`redacted_at` are lifecycle fields used by storage, retrieval, and index
maintenance; redacted units must not appear in normal reads.

## 9. MemoryUnit Style

MemoryUnits must be third-person and evidence-grounded.

Preferred:

```text
The user said they prefer concise Chinese answers.
The user asked the agent not to auto-commit code.
The user decided NanoMem should focus on long-term personal memory.
The agent auto-committed code and the user reacted negatively.
```

Avoid:

```text
I prefer concise Chinese answers.
Do not auto-commit code.
NanoMem should focus on long-term personal memory.
```

Why:

- it preserves who said, asked, decided, corrected, or experienced something;
- it prevents memories from masquerading as system instructions;
- it supports reasoning over conflicting facts;
- it works for multi-user and multi-agent conversations.

## 10. Memory Types

First-version `memory_type` values:

| Type | Meaning |
| --- | --- |
| `preference` | User preference or style choice |
| `correction` | User correction to agent behavior |
| `habit` | Durable repeated behavior or workflow pattern |
| `background` | Durable user background |
| `relationship` | Relationship with person, tool, organization, or agent |
| `user_event` | Important event or decision involving the user |
| `agent_interaction_event` | User-visible agent action that affects future collaboration |
| `uncertain` | Potentially useful fact whose type is not yet specific |

These labels are retrieval and policy aids. They should not become separate
storage systems. Custom memory types are out of scope for the first version;
experiment labels and product-specific classes belong in metadata.

## 11. Truth And Conflicts

NanoMem is an append-only evidence log, not a canonical user profile.

It should not automatically:

- replace old facts;
- mark one fact as current truth;
- merge facts into a single profile value;
- resolve semantic conflicts.

Instead, `read` returns relevant evidence with timestamps. The downstream agent
reasons about recency, scope, and conflict. Dialogue references remain available
in structured results, but rendering them is host-configurable.

## 12. Retrieval Objects

`IndexHit` is derived data:

```python
IndexHit:
  unit_id: str
  score: float
  retrieval_text: str
  score_breakdown: dict
```

`RankedMemoryUnit` combines a loaded MemoryUnit with ranking evidence:

```python
RankedMemoryUnit:
  unit: MemoryUnit
  rank: int
  score: float
  retrieval_text: str
  score_breakdown: dict
```

The index must never be the source of truth for MemoryUnit content.

## 13. Rendered Context

`PackedContext` is the final prompt-facing evidence block.

```python
PackedContext:
  text: str
  token_count: int
  unit_count: int
```

Rendering should maximize useful fact coverage under the post-render token
budget while preserving time evidence. Rendered text must include the
MemoryUnit timestamp for every item. Other display labels, such as dialogue
refs, namespace, memory type, tags, and project hints, are renderer-configurable
metadata.

## 14. Operation Logs

Operation logs record system behavior for inspection and maintenance.

They are not personal MemoryUnits and should have separate retention policy.

```python
OperationLogEntry:
  log_id: str
  operation_type: "capture" | "read" | ...
  created_at: str
  scope: MemoryScope
  status: str
  summary: dict
  payload: dict
```

Operation logs may include summaries and trace metadata. They must not store
raw dialogue content by default. If local inspection requires raw personal
content, it must be covered by retention policy and kept out of agent-facing
read paths.
