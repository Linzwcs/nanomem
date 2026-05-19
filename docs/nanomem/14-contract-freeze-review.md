# Contract Freeze Review

Status: draft

This document reviews the current core contracts before treating the first
public API shape as stable. The goal is to keep capture/read small, separate
agent-facing data from control-plane data, and avoid leaking algorithm knobs
into dialogue inputs.

## 1. Boundary Rules

- Public capture describes what the user and agent visibly said.
- Public read describes what the agent needs to know before answering.
- Extraction, ranking, rendering, and indexing policies are implementation or
  configuration concerns.
- Store and index contracts are internal extension points, not agent tools.
- `metadata` is the escape hatch for host-specific ids, not a place to recreate
  core fields.

## 2. Agent-Facing Contracts

### CaptureRequest

Fields:

- `scope`: identifies whose personal memory is being written.
- `dialogue`: bounded user-visible message list.
- `capture_time`: when NanoMem accepted the capture.

Design decision:

- No `options`, no `chunk_size`, no extractor controls. Capture callers provide
  evidence; NanoMem decides how to process it.

### CaptureDialogue

Fields:

- `messages`: the visible messages in this capture payload.
- `occurred_at`: when the dialogue occurred.
- `metadata`: host-defined JSON, such as a local log pointer.

Design decision:

- A dialogue is one captured message list, not a session, project, turn, or raw
  transcript database.
- It has no namespace because it is evidence, not a memory unit.

### DialogueMessage

Fields:

- `role`: visible function, usually `user` or `assistant`.
- `content`: message text.
- `timestamp`: required evidence time.
- `speaker_id`: stable attribution id, optional.
- `metadata`: host-defined JSON.

Design decision:

- `speaker_name` is omitted because names are display metadata and can drift.
- Tool/raw result roles are skipped by extraction and should not become normal
  memory evidence.

### ReadRequest

Fields:

- `owner_id`: whose memory to read.
- `namespaces`: optional allow-list; `None` means all namespaces for the owner.
- `query`: natural language or structured query.
- `query_time`: required time anchor for recency scoring.
- `time_range`: optional hard filter.
- `recency_policy`: optional override; service default is used when omitted.
- `max_units`: optional result count cap.
- `context_budget_tokens`: optional render budget.
- `metadata`: host-defined JSON.

Design decision:

- Read is owner-centered, not session/project/agent-centered.
- Time range filters candidates; recency policy only affects ranking.

## 3. Evidence And Memory Contracts

### DialogueRecord

Fields:

- `dialogue_id`: stable evidence id.
- `messages`: archived visible message list.
- `captured_at`: capture acceptance time.
- `occurred_at`: source dialogue time.
- `checksum`: optional integrity marker.
- `metadata`: host-defined JSON.
- `retention_until`, `redacted_at`: lifecycle fields.

Design decision:

- It is control-plane evidence and is not returned by normal read.
- It has no `owner_id` or `namespace`; produced MemoryUnits carry scope.

### DialogueRef

Fields:

- `dialogue_id`: evidence record id.
- `message_range`: half-open message range, optional.

Design decision:

- Refs point to dialogue message ranges only. No char ranges, file refs, image
  refs, or external resource refs in v1.

### MemoryUnit

Fields:

- `unit_id`: stable id for a fact-like memory.
- `scope`: `owner_id` and resolved namespace.
- `text`: durable personal fact text.
- `memory_type`: preference, correction, background, event, etc.
- `timestamp`: evidence time.
- `available_at`: NanoMem acceptance time.
- `dialogue_refs`: evidence pointers.
- `confidence`: extractor confidence, optional.
- `retention_until`, `redacted_at`: lifecycle fields.
- `metadata`: host/extractor-defined JSON.

Design decision:

- MemoryUnit is the authoritative retrieval object.
- It stores fact-level memory, not raw chunks.
- Conflicts are preserved as separate facts until a future consolidation layer
  is deliberately added.

## 4. Internal Pipeline Contracts

### ExtractionRequest

Fields:

- `scope`: resolved memory scope.
- `dialogue`: archived DialogueRecord.

Design decision:

- Extraction operates on stored evidence, not raw request JSON.
- Chunking is extractor policy/configuration, not a request parameter.

### ExtractionResult

Fields:

- `units`: extracted MemoryUnits.
- `skipped`: skipped message ranges and reasons.
- `stats`: extractor diagnostics.

Design decision:

- Skip reasons are first-class so hosts can inspect why content was not stored.

### IndexSearchRequest

Fields:

- `owner_id`: required owner filter.
- `namespaces`: optional namespace filter.
- `query`: retrieval text.
- `time_range`: optional hard filter.
- `limit`: optional candidate cap.
- `metadata`: future backend-specific hints.

Design decision:

- Indexes are derived and rebuildable. They never own MemoryUnit truth.

### MemoryUnitSelector

Fields:

- filters over owner, namespace, ids, time, type, redaction state, limit, order.

Design decision:

- This is a store/admin selector, not an agent-facing read request.

### OperationLogEntry

Fields:

- `log_id`, `operation_type`, `created_at`, optional `scope`, `status`,
  `summary`, and `payload`.

Design decision:

- Operation logs are append-only diagnostics. They use runtime-unique ids, not
  stable content ids.

### ReindexResult

Fields:

- `indexed_unit_count`: number of units loaded from store into index.
- `index_backend`: active index backend name.
- `stats`: selector and backend diagnostics.

Design decision:

- Reindex is a control-plane operation for rebuilding derived indexes from the
  authoritative store.

## 5. Freeze Candidates

Likely stable for v1:

- `MemoryScope(owner_id, namespace)`
- `CaptureRequest(scope, dialogue, capture_time)`
- `ReadRequest(owner_id, namespaces, query, query_time, ...)`
- `MemoryUnit` fact-level shape
- `DialogueRecord` as non-agent-facing evidence

Still flexible:

- `memory_type` taxonomy;
- extraction skip reason names;
- ranking score breakdown keys;
- render text format;
- metadata conventions.

## 6. Explicit Non-Goals For V1

- no session/project/tenant fields in core scope;
- no request-level capture idempotency;
- no `chunk_size` or extraction algorithm knobs in capture requests;
- no raw multimodal/file/source refs in MemoryUnit;
- no ANN implementation in core.
