# Interfaces And Integration

Status: draft

This document defines the core interfaces NanoMem should stabilize before HTTP,
MCP, SDK, or agent adapters.

The goal is a small, durable contract: adapters may change, stores may change,
indexes may change, and extraction providers may change without changing what
NanoMem means by capture, read, memory, dialogue evidence, or rendered context.

## 1. Design Rule

Core interfaces come first. Transport adapters must map onto the same service
contract and must not introduce new memory semantics.

```text
HTTP / MCP / SDK / agent hooks
  -> NanoMemService
  -> store / index / extractor / ranker / renderer
```

The service contract is the semantic boundary. Everything above it is transport
shape. Everything below it is replaceable capability.

Core invariants:

- time is mandatory and first-class;
- `metadata` is host-defined JSON and must not replace core fields;
- request namespace may be omitted, but stored MemoryUnits must carry a
  resolved non-null namespace;
- `CaptureDialogue` is a bounded message payload, not a session;
- `CaptureRequest.session_id` is optional; when present, it groups multiple
  capture payloads into one appendable dialogue window;
- `Dialogue` is raw control-plane evidence, not agent-facing memory;
- Session, Dialogue, and DialogueWindow do not carry memory owner or
  namespace; MemoryUnit is the first durable owner/namespace object;
- rendered MemoryUnits must include time;
- NanoMem stores dialogue refs, not external resource refs, as first-version
  evidence.

## 2. Core Objects

The core contract objects are:

```text
MemoryScope
Session
DialogueMessage
CaptureDialogue
Dialogue
DialogueWindow
DialogueRef
MemoryUnit
FlushRequest / FlushResult
CaptureRequest / CaptureResult
ReadRequest / ReadResult
RankedMemoryUnit
PackedContext
```

They should live in a dependency-light contracts module. HTTP schemas,
Pydantic models, CLI parsing, and MCP payload shaping are adapter concerns.

### MemoryScope

`MemoryScope` identifies the memory owner and stable namespace.

```python
MemoryScope:
  owner_id: str
  namespace: str | None
```

Responsibility:

- bind extracted MemoryUnits and reads to a person or named speaker;
- keep memory spaces stable across sessions and projects;
- give storage, retrieval, and retention a common MemoryUnit key.

Why it is separate:

- owner and namespace are core semantics, not transport metadata;
- namespaces are stable memory categories, while tags, projects, agents, and
  experiments are flexible metadata.

It must not:

- encode temporary session, run, task, or repository ids;
- be stored on Session, Dialogue, or DialogueWindow;
- be invented by extractors;
- be overridden by `metadata`.

### DialogueMessage

`DialogueMessage` is one user-visible message in a capture payload or archived
dialogue.

```python
DialogueMessage:
  role: str
  content: str
  speaker_id: str | None
  timestamp: str
```

Responsibility:

- preserve the visible words used as evidence;
- preserve message-level time for extraction and audit;
- preserve stable speaker attribution without making speaker identity part of
  storage scope.

Why it is separate:

- it is evidence input, not a durable personal fact;
- it belongs to dialogue archiving and extraction, not read rendering.

It must not:

- contain hidden reasoning, tool calls, raw tool results, or raw files;
- use metadata to replace `timestamp`;
- become an indexed retrieval unit.

`role` is a visible dialogue function, such as `user`, `assistant`,
`system_visible`, or `other`. `speaker_id` is a stable actor id for a user,
agent, or named participant. Display names stay in metadata.

### CaptureDialogue

`CaptureDialogue` is the bounded source payload supplied to `capture`.

```python
CaptureDialogue:
  messages: tuple[DialogueMessage, ...]
  occurred_at: str
  metadata: dict
```

Responsibility:

- carry one bounded batch of user-visible dialogue into the capture pipeline;
- provide the dialogue occurrence time and adapter audit metadata;
- become a `Dialogue` before extraction.

Why it is separate:

- hosts may have long-running, concurrent, or multi-day sessions, but NanoMem
  only needs bounded capture calls;
- request payload shape is distinct from stored control-plane evidence.

It must not:

- represent a session lifecycle, conversation object, transcript archive, or
  replay window;
- carry required host ids beyond core fields;
- include hidden reasoning, tool streams, logs, or raw multimodal assets.

### Session, Dialogue, DialogueWindow, And DialogueRef

`Session` groups related capture streams. `Dialogue` stores raw
visible messages. `DialogueWindow` controls buffering and extraction lifecycle.
`DialogueRef` links a MemoryUnit back to raw evidence.

```python
Session:
  session_id: str
  created_at: str
  updated_at: str
  metadata: dict
```

```python
Dialogue:
  dialogue_id: str
  session_id: str | None
  messages: tuple[DialogueMessage, ...]
  started_at: str
  ended_at: str
  created_at: str
  updated_at: str
  checksum: str | None
  metadata: dict
  retention_until: str | None
  redacted_at: str | None
```

```python
DialogueWindow:
  session_id: str
  dialogue_id: str
  status: "open" | "sealed" | "extracting" | "extracted" | "failed"
  token_count: int
  message_count: int
  created_at: str
  updated_at: str
  sealed_at: str | None
  extracted_at: str | None
  seal_reason: str | None
  metadata: dict
```

```python
DialogueRef:
  dialogue_id: str
  message_range: tuple[int, int] | None
```

Responsibility:

- group concurrent host sessions without adding memory semantics;
- support audit, debugging, deletion, redaction, and re-extraction;
- control append/seal/extract/retry lifecycle separately from raw messages;
- give accepted MemoryUnits evidence lineage;
- keep raw dialogue retention separate from MemoryUnit retention.

Why they are separate:

- `Dialogue` is a durable control-plane object;
- `DialogueWindow` is mutable lifecycle control for a dialogue;
- `DialogueRef` is a compact evidence pointer stored on MemoryUnits;
- normal read needs MemoryUnits and rendered evidence, not raw dialogue.

They must not:

- be indexed as retrieval candidates;
- be returned by agent-facing read;
- be rendered into prompt context;
- carry `owner_id`, `namespace`, or `MemoryScope`;
- introduce external resource references as first-version evidence.

`session_id` is authoritative only for grouping raw messages into the same
session. Memory ownership and namespace are assigned when MemoryUnits are
created. A capture request may provide routing context, but that context is not
part of the raw dialogue contract.

`DialogueRef.message_range` is optional. The default is `None`, meaning the
whole source dialogue is evidence. If an extractor later provides precise
attribution, the range is a half-open message-index range `[start, end)`. It is
not a token, byte, or character range.

### MemoryUnit

`MemoryUnit` is the durable personal fact NanoMem stores and retrieves.

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

Responsibility:

- store one durable, third-person personal fact;
- carry owner, resolved namespace, time, availability, lifecycle state, and
  evidence refs;
- provide the authoritative content for indexing, ranking, and rendering.

Why it is separate:

- it is derived from dialogue but is not raw dialogue;
- it is authoritative storage content, while index hits are derived candidates;
- it is evidence for agents, not a canonical user profile.

It must not:

- store workspace documents, raw logs, raw files, tool outputs, or full chats;
- use `metadata` to redefine owner, namespace, timestamp, or retention state;
- replace older conflicting facts through capture;
- be treated as an imperative instruction by renderers.

## 3. Service API

`NanoMemService` is the only normal application entry point.

```python
class NanoMemService:
    def capture(self, request: CaptureRequest) -> CaptureResult:
        ...

    def flush(self, request: FlushRequest | None = None) -> FlushResult:
        ...

    def read(self, request: ReadRequest) -> ReadResult:
        ...
```

Responsibility:

- validate owner, namespace, time, and metadata shape;
- archive or append raw `Dialogue` before extraction;
- flush sealed/open dialogue windows into MemoryUnits when requested;
- orchestrate extraction, storage, indexing, ranking, and rendering;
- write operation logs;
- keep admin operations out of agent-facing tools.

Why it exists:

- adapters need one semantic contract to call;
- capability implementations need one orchestration owner;
- policy decisions such as namespace validation and post-render
  budgeting should not leak into transports or backends.

Why it is separated from adjacent interfaces:

- adapters parse and serialize external payloads;
- stores persist authoritative records;
- indexes return candidates;
- extractors propose MemoryUnits;
- rankers and renderers shape read output.

The service must not:

- depend on HTTP, MCP, LanceDB, pgvector, or a concrete LLM provider;
- let adapters bypass store/index/ranker/renderer boundaries for normal memory
  operations;
- expose backup, export, retention, delete, reindex, or Dialogue inspect
  as ordinary agent tools.

## 4. Store Interface

The store owns durable facts and control-plane records.

```python
class MemoryStore:
    def append_units(self, units: tuple[MemoryUnit, ...]) -> None: ...
    def get_units(self, unit_ids: tuple[str, ...]) -> tuple[MemoryUnit, ...]: ...
    def query_units(self, selector: UnitSelector) -> tuple[MemoryUnit, ...]: ...
    def put_session(self, session: Session) -> None: ...
    def put_dialogue(self, dialogue: Dialogue) -> None: ...
    def get_dialogue(self, dialogue_id: str) -> Dialogue | None: ...
    def put_dialogue_window(self, window: DialogueWindow) -> None: ...
    def query_dialogue_windows(
        self,
        selector: DialogueWindowSelector,
    ) -> tuple[DialogueWindow, ...]: ...
    def append_operation_log(self, entry: OperationLogEntry) -> None: ...
```

Responsibility:

- persist MemoryUnits, sessions, raw Dialogues, windows, and operation logs;
- enforce authoritative lookup and filtering over stored records;
- preserve ids, timestamps, dialogue refs, metadata, and retention state.

Why it exists:

- retrieval indexes are derived and may be stale or rebuilt;
- admin operations need authoritative data independent of search backends;
- migrations, backup, export, and privacy controls need one durable boundary.

Why it may be split:

- implementations may expose `MemoryUnitStore`, `DialogueArchive`, and
  `OperationLogStore` internally;
- the service should still see one storage capability so capture/read ordering
  and transaction boundaries remain coherent.

The store must not:

- perform ranking, rendering, embedding, or ANN search;
- treat `metadata` as a schema for core semantics;
- expose Dialogues through normal agent-facing reads;
- put MemoryUnit owner/namespace onto raw Dialogues or DialogueWindows;
- make index data required for correctness.

## 5. Index Interface

The index returns candidates only.

```python
class MemoryUnitIndex:
    def upsert(self, units: tuple[MemoryUnit, ...]) -> None: ...
    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]: ...
    def delete(self, unit_ids: tuple[str, ...]) -> None: ...
    def clear(self) -> None: ...
```

Responsibility:

- accelerate retrieval over MemoryUnits;
- return candidate ids and search scores;
- apply owner, namespace, and time filters when the backend supports them;
- duplicate only configured metadata filter keys, not arbitrary metadata;
- remain rebuildable from the store.

Why it exists:

- lexical, dense, hybrid, LanceDB, and pgvector backends have different
  operational shapes;
- NanoMem core should not implement ANN algorithms;
- candidate retrieval is a performance concern, not the source of truth.

Why it is separate from the store:

- the store preserves authoritative records;
- the index may duplicate retrieval text, vectors, and selected filter fields;
- failed or stale index state must not corrupt MemoryUnits.

The index must not:

- return authoritative MemoryUnit text;
- expose backend-specific types to service code;
- index Dialogues or raw dialogue;
- decide final ranking, conflict handling, or rendered output.

## 6. Extraction Interface

The extractor proposes MemoryUnits from bounded dialogue evidence.

```python
class MemoryExtractor:
    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        ...
```

Responsibility:

- read normalized user-visible dialogue;
- produce accepted candidate MemoryUnits and explicit skip reasons;
- preserve evidence grounding through message ranges;
- avoid non-personal, workspace-local, hidden, or tool-derived material.

Why it exists:

- extraction may be rule-based, model-backed, or hybrid;
- quality gates and skip reasons need a common result shape;
- capture orchestration should not depend on a provider API.

Why it is separate from the service and store:

- the service validates scope, archive order, and persistence;
- the store persists accepted units;
- the extractor only proposes facts from evidence.

The extractor must not:

- write to storage or indexes;
- invent owners or namespaces;
- perform semantic truth maintenance or canonical profile synthesis;
- use host metadata as a substitute for required time, scope, or dialogue
  content.

Extractor output should make operator decisions visible: accepted facts,
message ranges, and skip reasons are all part of capture quality.

## 7. Ranking And Rendering

Ranking orders structured evidence. Rendering produces prompt-ready text.

```python
class MemoryRanker:
    def rank(self, request: RankRequest) -> tuple[RankedMemoryUnit, ...]:
        ...

class ContextRenderer:
    def render(self, request: RenderRequest) -> PackedContext:
        ...
```

Ranker responsibility:

- combine retrieval scores, recency, namespace, time range, memory type, and
  host metadata hints;
- keep relevant conflicts visible when useful;
- produce ordered `RankedMemoryUnit` evidence with score traces.

Renderer responsibility:

- render ranked MemoryUnits into compact prompt evidence;
- enforce the post-render token budget;
- include time for every rendered MemoryUnit;
- preserve third-person MemoryUnit text.

Why they are separate:

- ranking is structured selection and ordering;
- rendering is text packing under a final budget;
- a renderer may drop optional labels to fit more facts without changing ranker
  scoring.

They must not:

- decide canonical truth or delete conflicting facts;
- turn memories into direct instructions;
- render raw Dialogue content;
- dump raw metadata;
- omit time from any rendered MemoryUnit.

All labels other than time are renderer-configurable, including namespace,
memory type, tags, project hints, and dialogue refs.

## 8. Transport Adapters

HTTP, MCP, CLI, and SDK adapters should only:

- parse external payloads;
- validate transport-specific shape;
- convert to core contracts;
- call `NanoMemService`;
- serialize results.

Why this boundary exists:

- transport APIs evolve faster than core contracts;
- different adapters need different validation and authentication surfaces;
- normal memory behavior should be identical across HTTP, MCP, SDK, and local
  agent hooks.

Adapters must not:

- access stores or indexes directly for normal memory operations;
- expose Dialogues through agent-facing read;
- expose backup, export, retention, delete, or reindex as ordinary agent tools;
- reinterpret `metadata` as core semantics;
- relax mandatory time requirements by hiding unknown time in metadata.

Convenience adapters may fill omitted request time from the host clock, but
they must pass a concrete timestamp into the core service.

## 9. Agent Integration Pattern

Before a turn:

```text
agent reads workspace/tools
agent calls NanoMem.read(owner_id, namespaces, query, query_time, budget)
agent adds PackedContext.text as personal evidence
```

After a turn:

```text
agent sends bounded CaptureDialogue to NanoMem.capture
NanoMem extracts durable personal MemoryUnits
agent does not send hidden reasoning, tools, logs, or raw files
```

For concurrent or long-running sessions, the host simply calls `capture`
multiple times. NanoMem does not model session lifecycle.

This pattern keeps workspace state, tool state, and long-running session state
outside NanoMem while still preserving durable personal facts that matter across
turns and projects.

Behavior examples live in `11-behavior-cases.md`. This document keeps the
interface boundary focused.

## 10. Admin Boundary

Admin operations should use a separate control-plane service or CLI:

```text
backup
export
retention preview/apply
delete/redact
reindex
integrity check
inspect Dialogue
```

These operations may read Dialogues and operation logs. They must not be
available through normal agent-facing memory tools.

The boundary is intentional: agent tools need compact capture/read behavior,
while admin tools need privacy, retention, audit, and operational authority.
