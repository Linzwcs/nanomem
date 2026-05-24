# Contract Freeze Review

Status: v1 freeze candidate

This document records the current public contract shape after code and tests
were reviewed. The goal is to freeze the small agent-facing API before adding
LLM extraction, persistent vector indexes, and richer manager operations.

## 1. Boundary Rules

- Public capture describes visible dialogue evidence.
- Public read describes what an agent needs before answering.
- `MemoryUnit` is the durable retrieval object.
- `DialogueRecord` is audit evidence and is not returned by normal read.
- Indexes are derived and rebuildable from the authoritative store.
- `metadata` is the host escape hatch; it must not replace core fields.

## 2. Freeze Candidates

These shapes should be treated as stable unless a breaking-change review is
explicitly opened.

```python
MemoryScope(owner_id: str, namespace: str | None = None)
```

`owner_id` identifies whose personal memory is being read or written.
`namespace` is a stable host-defined category. It is not a tag list.

```python
DialogueMessage(
  role: str,
  content: str,
  timestamp: str,
  speaker_id: str | None = None,
  metadata: dict = {},
)
```

`role` is visible function, usually `user` or `assistant`.
`speaker_id` is stable attribution. `speaker_name` remains omitted because
display names drift.

```python
CaptureDialogue(
  messages: tuple[DialogueMessage, ...],
  occurred_at: str,
  metadata: dict = {},
)
```

A dialogue is one captured visible message list. It is not a session, turn,
project, or transcript database.

```python
CaptureRequest(
  scope: MemoryScope,
  dialogue: CaptureDialogue,
  capture_time: str,
  session_id: str | None = None,
)
```

Capture has no `chunk_size`, idempotency key, extractor options, or index
controls. `session_id` is only a routing key for dialogue buffering. Other
algorithm choices are implementation/configuration concerns.

```python
DialogueRecord(
  dialogue_id: str,
  scope: MemoryScope,
  session_id: str | None,
  messages: tuple[DialogueMessage, ...],
  status: "open" | "sealed" | "extracted" | "failed",
  started_at: str,
  ended_at: str,
  created_at: str,
  updated_at: str,
  token_count: int,
  checksum: str | None = None,
  metadata: dict = {},
  extracted_at: str | None = None,
  retention_until: str | None = None,
  redacted_at: str | None = None,
)
```

Dialogue records are control-plane evidence. They carry scope/session for
storage routing and filtering, but produced memory units remain the
agent-facing facts.

```python
DialogueRef(
  dialogue_id: str,
  message_range: tuple[int, int] | None = None,
)
```

`message_range` is a half-open range over `DialogueRecord.messages`. No char
ranges, file refs, image refs, or external resource refs are in v1.

```python
MemoryUnit(
  unit_id: str,
  scope: MemoryScope,
  text: str,
  memory_type: str,
  timestamp: str,
  available_at: str,
  dialogue_refs: tuple[DialogueRef, ...] = (),
  retention_until: str | None = None,
  redacted_at: str | None = None,
  metadata: dict = {},
)
```

Memory units store fact-level personal memory, not raw chunks. Conflicts remain
as separate facts until a future consolidation layer is added.

```python
ReadRequest(
  owner_id: str,
  namespaces: tuple[str, ...] | None,
  query: str | dict,
  query_time: str,
  time_range: TimeRange | None = None,
  recency_policy: "recent" | "balanced" | "historical" | None = None,
  max_units: int | None = None,
  context_budget_tokens: int | None = None,
  metadata: dict = {},
)
```

`namespaces=None` means search all namespaces for the owner. `query_time` is the
anchor for recency scoring. `time_range` is a hard candidate filter.

## 3. Response Contracts

```python
CaptureResult(
  dialogue_id: str,
  accepted_message_count: int,
  unit_count: int,
  units: tuple[MemoryUnit, ...],
  skipped: tuple[CaptureSkip, ...] = (),
  stats: dict = {},
  trace_ref: str | None = None,
)
```

```python
ReadResult(
  request: ReadRequest,
  ranked_units: tuple[RankedMemoryUnit, ...],
  context: PackedContext,
  stats: dict = {},
  trace_ref: str | None = None,
)
```

`ReadResult.ranked_units` is structured evidence. `PackedContext.text` is the
agent-facing rendered memory context and must include timestamps for rendered
facts.

## 4. Compatibility Rules

Current JSON parsing intentionally keeps these compatibility aliases:

- `scope.user_id` is accepted as `owner_id`;
- legacy capture `events` are mapped into `CaptureDialogue.messages`;
- legacy event `speaker` is mapped into `DialogueMessage.speaker_id`;
- legacy `event_type` values `preference` and `correction` are copied into
  message metadata as `memory_type`.

These aliases are input compatibility only. New examples should use the frozen
field names.

## 5. Wire JSON Rules

Public serializers emit canonical JSON-compatible objects:

- tuples are serialized as JSON arrays;
- `scope.user_id` is never emitted, only `scope.owner_id`;
- legacy `events` are never emitted, only `dialogue.messages`;
- `DialogueRef.message_range` is emitted as a two-item array;
- `namespaces=None` is emitted as JSON `null` and means all namespaces for the
  owner;
- explicit namespace filters are emitted as ordered arrays;
- response `stats` remain a diagnostics object and individual keys are not part
  of the frozen semantic contract unless documented elsewhere.

HTTP, SDK, MCP structured results, and Manager retrieval preview should all use
these same wire shapes.

## 6. Integration Surfaces

Frozen agent-facing surfaces:

- HTTP `POST /v1/capture`;
- HTTP `POST /v1/read`;
- Python SDK `NanoMemClient.capture` and `NanoMemClient.read`;
- MCP tool `nanomem_read`.

Control-plane surfaces that mirror read contracts but remain manager-specific:

- Manager `POST /manager/api/retrieval-preview`;
- Manager `GET /manager/api/memory-units`;
- Manager `GET /manager/api/memory-units/{unit_id}`;
- Manager `GET /manager/api/operation-logs`.

Manager preview must preserve `query_time`, `time_range`, `max_units`, and
`context_budget_tokens` in the normalized `ReadRequest` that appears in the
response. `query_time` affects recency ranking; `time_range` is a hard evidence
timestamp filter.

## 7. Internal Extension Contracts

These remain internal and may evolve without breaking agent-facing API:

- `ExtractionRequest`
- `ExtractionResult`
- `IndexSearchRequest`
- `IndexHit`
- `MemoryUnitSelector`
- `OperationLogSelector`
- `OperationLogEntry`
- `ReindexResult`

They are still important for extension authors, but they are not normal agent
tools.

## 8. Validated Behaviors

Contract tests now cover:

- capture JSON parsing and serialization;
- read JSON parsing and serialization;
- capture result and read result JSON round trips;
- public JSON serializers returning arrays, not Python tuples;
- HTTP `400` contract errors for malformed requests;
- SDK error wrapping for HTTP contract failures;
- MCP tool schema for `nanomem_read` and rejection of capture tool calls;
- MCP tool calls returning structured public results;
- Manager retrieval preview preserving read tuning fields;
- request/response example JSON blocks parsing successfully;
- examples avoiding legacy emitted fields such as `user_id` and `events`;
- legacy event payload compatibility;
- `namespaces=None` meaning all namespaces;
- explicit namespace lists preserving order;
- `DialogueRef.message_range` parsing as a two-item half-open range;
- invalid `message_range` rejection;
- metadata fields requiring JSON objects;
- service-level rejection of missing message timestamps;
- unsupported `recency_policy` rejection.

Validation command:

```bash
python -m pytest tests/test_serde.py tests/server/test_http_sdk.py tests/server/test_manager_console.py tests/mcp/test_schema.py tests/docs/test_request_response_examples.py
```

## 9. Still Flexible

These should not be frozen yet:

- `memory_type` taxonomy;
- extraction skip reason names;
- score breakdown keys;
- render text format;
- metadata conventions;
- persistent vector backend configuration.

## 10. Explicit Non-Goals For V1

- no session/project/tenant fields in `MemoryScope`;
- no request-level capture idempotency;
- no `chunk_size` or extraction algorithm knobs in capture request;
- no raw multimodal/file/source refs in `MemoryUnit`;
- no direct raw dialogue indexing;
- no login/auth requirement for the local manager.
