# NanoMem Code Architecture

Status: draft

This document defines the intended code architecture for NanoMem as a
production long-term personal memory backend. It follows the product boundary in
`docs/nanomem-product-rfc.md`.

For the top-level system design, see `docs/system-design.md`.

For the agent-harness memory model and scenario-specific read/write guidance,
see `docs/agent-memory-positioning.md`.

For architecture diagrams and the storage/index split, see
`docs/architecture-overview.md`.

For index backend selection, including in-memory, LanceDB, and Postgres/pgvector
paths, see `docs/index-backends.md`.

NanoMem is separate from `memexp`. `memexp` is the experiment platform.
NanoMem is the production backend that may receive promoted ideas from
`memexp` after evaluation.

## 1. Architecture Goal

Build a small server-backed memory system with two agent-facing operations:

```text
capture
read
```

The implementation should optimize for:

- narrow product scope;
- append-only personal fact units;
- explicit time filtering with recency-aware ranking;
- required time preservation and optional trace metadata;
- engineering lifecycle maintenance;
- clear adapters for OpenClaw-like agents;
- clean evaluation through `memexp`.

The implementation should not become:

- an agent framework;
- a document ingestion system;
- a codebase memory system;
- a project state database;
- a workspace search replacement;
- a canonical user profile service.

## 2. Package Boundary

Production code should live in a top-level `nanomem` package:

```text
src/
  nanomem/
  memexp/
```

Dependency rule:

```text
nanomem must not import memexp
memexp may import nanomem only through an adapter or SDK path
```

This keeps production service code independent from benchmark datasets,
experiment manifests, staged artifacts, and evaluator logic.

## 3. Proposed Layout

```text
src/
  nanomem/
    __init__.py

    contracts.py
    config.py
    factory.py
    errors.py
    ids.py
    time.py

    policies.py

    service/
      __init__.py
      async_core.py
      core.py
      capture.py
      read.py

    extraction/
      __init__.py
      base.py
      heuristic.py
      llm.py
      prompts.py

    store/
      __init__.py
      base.py
      sqlite.py

    index/
      __init__.py
      base.py
      lexical.py
      dense.py
      hybrid.py

    embeddings/
      __init__.py
      base.py
      hashing.py
      openai_compatible.py

    ranking/
      __init__.py
      ranker.py
      recency.py

    render/
      __init__.py
      context.py

    maintenance/
      __init__.py
      retention.py
      compaction.py
      redaction.py

    admin/
      __init__.py
      service.py

    cli/
      __init__.py
      __main__.py
      main.py

    tui/
      __init__.py
      dashboard.py

    server/
      __init__.py
      __main__.py
      app.py
      main.py
      routes.py
      schemas.py
      auth.py

    sdk/
      __init__.py
      client.py

    adapters/
      __init__.py
      openclaw.py
      mcp.py

  memexp/
    ...
```

The first implementation does not need every file above. The layout defines the
target boundaries so early code does not collapse unrelated concerns together.

## 4. Dependency Direction

Allowed dependency direction:

```text
server -> service -> extraction / store / index / ranking / render -> contracts
maintenance -> store / index / contracts
cli -> admin -> store / index / contracts
tui -> admin / contracts
adapters -> sdk / contracts
sdk -> contracts
```

Not allowed:

```text
contracts -> server
contracts -> store
service -> server
store -> service
index -> service
cli -> store
cli -> index
tui -> store
tui -> index
nanomem -> memexp
```

The service layer owns orchestration. Stores and indexes expose capabilities but
do not decide capture or read behavior.

## 5. Core Contracts

`nanomem.contracts` should be dependency-light. Prefer standard-library
dataclasses or typed protocol objects in core contracts. HTTP-specific Pydantic
models, if used, belong in `nanomem.server.schemas`.

Primary contracts:

```python
MemoryScope:
  owner_id: str
  namespace: str | None

DialogueMessage:
  role: str
  content: str
  speaker_id: str | None
  timestamp: str

CaptureDialogue:
  messages: tuple[DialogueMessage, ...]
  occurred_at: str
  metadata: dict

DialogueRef:
  dialogue_id: str
  message_range: tuple[int, int] | None

DialogueRecord:
  dialogue_id: str
  messages: tuple[DialogueMessage, ...]
  captured_at: str
  occurred_at: str
  checksum: str | None
  metadata: dict
  retention_until: str | None
  redacted_at: str | None

MemoryUnit:
  unit_id: str
  scope: MemoryScope
  text: str
  memory_type: str
  timestamp: str
  available_at: str
  dialogue_refs: tuple[DialogueRef, ...]
  confidence: float | None
  retention_until: str | None
  redacted_at: str | None
  metadata: dict
```

`DialogueRecord` is control-plane evidence and should not carry `owner_id` or
`namespace`; one dialogue can produce MemoryUnits for multiple owners or
namespaces. Host-specific ids such as conversation id, turn id, and log
pointers belong in metadata, not in the core contract.

Agent-facing requests:

```python
CaptureRequest:
  scope: MemoryScope
  dialogue: CaptureDialogue
  capture_time: str

ReadRequest:
  owner_id: str
  namespaces: tuple[str, ...] | None
  query: str | dict
  query_time: str
  time_range: TimeRange | None
  recency_policy: str
  max_units: int | None
  context_budget_tokens: int | None
  metadata: dict
```

Agent-facing responses:

```python
CaptureResult:
  dialogue_id: str
  accepted_message_count: int
  unit_count: int
  units: tuple[MemoryUnit, ...]
  skipped: tuple[CaptureSkip, ...]
  stats: dict
  trace_ref: str | None

ReadResult:
  ranked_units: tuple[RankedMemoryUnit, ...]
  context: PackedContext
  stats: dict
  trace_ref: str | None
```

## 6. Service Layer

`NanoMemService` is the central in-process API used by the server and tests.

```python
class NanoMemService:
    def capture(self, request: CaptureRequest) -> CaptureResult:
        ...

    def read(self, request: ReadRequest) -> ReadResult:
        ...
```

`AsyncNanoMemService` is the async facade used by ASGI servers and async agent
runtimes:

```python
class AsyncNanoMemService:
    async def capture(self, request: CaptureRequest) -> CaptureResult:
        ...

    async def read(self, request: ReadRequest) -> ReadResult:
        ...
```

The initial async facade may delegate to the synchronous service through a
worker thread while serializing calls around single-node SQLite and in-memory
index backends. Later production backends can replace this with native async
store and index implementations without changing the agent-facing API.

It wires together:

- capture policy;
- extractor;
- unit store;
- retrieval index;
- ranking policy;
- context renderer;
- retention policy;
- trace sink.

The service layer should be deterministic where possible. External LLM calls
belong behind extractor interfaces and must record model/config metadata in
unit metadata or trace records.

## 7. Capture Pipeline

`service.capture` is not a generic add-memory endpoint. It receives
user-visible dialogue and appends personal fact units only.

Assistant messages are eligible only when they are final user-visible replies.
Reasoning, hidden thought, tool calls, and tool results must be skipped before
they can become MemoryUnits.

Messages may include stable `speaker_id` values. Extraction uses `role` and
`speaker_id` for attribution, but first-version capture writes accepted units
under the request owner and resolved namespace. Ambiguous attribution should be
skipped with an explicit reason rather than stored under a guessed owner.

Pipeline:

```text
CaptureRequest
  -> validate scope and dialogue
  -> archive DialogueRecord
  -> normalize dialogue messages
  -> split long dialogues into chunks of size n
  -> annotate chunks by role and speaker_id
  -> filter non-personal workspace facts
  -> extract candidate personal fact units with attribution
  -> attach DialogueRefs
  -> apply light quality gates
  -> append units to store
  -> update retrieval index
  -> return units and skipped reasons
```

Chunking is an extraction aid, not the storage model. The durable record remains
the extracted `MemoryUnit`. The chunk size `n` should be configurable by the
extractor or capture policy so experiments can compare quality and cost without
changing the external API.

Role-aware extraction is required for multi-actor turns. A fact extracted from a
user message, assistant final reply, or named speaker segment must retain enough
speaker attribution for downstream ranking, rendering, and audit.

Allowed capture behavior:

- append extracted units;
- skip workspace-local facts;
- skip low-confidence or empty units;
- record extraction traces.

Disallowed capture behavior in the primary path:

- semantic deduplication;
- replacing older units;
- marking one unit as the current truth;
- ingesting project documents;
- storing raw tool logs as memory.

Capture should store a bounded `DialogueRecord` through a separate
control-plane path before extraction. It must not be indexed, rendered, or
exposed through normal agent-facing read tools.

## 8. Read Pipeline

`service.read` retrieves personal fact units as evidence.

Pipeline:

```text
ReadRequest
  -> validate owner and namespaces
  -> resolve explicit time range, if provided
  -> retrieve candidates from index/store
  -> rank by relevance, recency, namespace match, and policy
  -> select facts for the post-render token budget
  -> render evidence context with maximum useful fact coverage
  -> return typed units and context
```

Default reads should not hard-filter old memories when `time_range` is omitted.
Recency remains a ranking signal; strict historical bounds require explicit
request settings.

Read must not return a canonical profile value. It should return enough
evidence for the caller's LLM to reason over time and scope.

The renderer is part of retrieval quality, not just presentation. Under the
same `context_budget_tokens`, the desired renderer should maximize the number
of relevant facts that survive after formatting and required timestamps are
included. Optional labels such as dialogue refs, namespace, confidence, tags,
and project hints are controlled by the host renderer. This favors compact
fact-level rendering over returning large raw chunks whose useful fact density
is lower.

## 9. Store Layer

The store is the durable source of personal fact units.

Protocol:

```python
class MemoryUnitStore:
    def append(self, units: tuple[MemoryUnit, ...]) -> None:
        ...

    def get(self, unit_id: str) -> MemoryUnit | None:
        ...

    def list_by_scope(
        self,
        scope: MemoryScope,
        time_range: TimeRange | None,
        limit: int | None,
    ) -> tuple[MemoryUnit, ...]:
        ...

    def redact(self, selector: RedactionSelector) -> RedactionResult:
        ...
```

Initial implementations:

- `sqlite`: current supported backend for local, single-user, and sidecar
  deployments.

The store owns durable MemoryUnits and operation logs. It should not also act as
a JSON-vector scan engine. SQLite is the default fact store; semantic vector
retrieval, if needed beyond the local dense index, should be added through a
separate `MemoryUnitIndex` adapter.

Store responsibilities:

- durable append;
- scope filtering;
- time filtering;
- retention metadata;
- redaction support;

Store non-responsibilities:

- semantic ranking;
- truth resolution;
- context rendering.

## 10. Index Layer

Indexes accelerate read. They are derived data, not the memory authority.

Protocol:

```python
class MemoryUnitIndex:
    def upsert(self, units: tuple[MemoryUnit, ...]) -> None:
        ...

    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]:
        ...

    def delete(self, unit_ids: tuple[str, ...]) -> None:
        ...
```

Supported first-slice indexes:

- `dense`: default scope-filtered, bounded embedding retrieval over unit text;
- `lexical`: token-overlap fallback and debugging baseline;
- `hybrid`: weighted lexical+dense retrieval.

The default dense embedding model is deterministic local hashing, so the system
can start without network access. OpenAI-compatible embedding models are
available as optional configured backends. Dense vectors are retrieval aids and
must not define the memory schema.

The local dense index must not scan the global corpus on every query. It should
bucket by owner/namespace scope and cap per-query similarity work with
`index.dense_scan_limit`. This is still not an ANN index; it is a dependency-free
local baseline for small deployments and experiments.

Future semantic retrieval should use a dedicated `MemoryUnitIndex` adapter, not
SQLite JSON-vector scanning. NanoMem should not implement ANN internally. Keep
the in-memory dense index as a simple bounded baseline, then delegate ANN to a
database-backed adapter when needed:

- LanceDB for embedded local vector persistence without running a server;
- Postgres + pgvector when the deployment wants the fact store and vector index
  in one operational database.

NanoMem should keep the adapter boundary small: upsert MemoryUnit vectors,
search by scope/time/query vector, delete by unit id, and clear/rebuild.

## 11. Extraction Layer

Extractors turn events into personal fact units.

Protocol:

```python
class MemoryUnitExtractor:
    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        ...
```

Implementations:

- `heuristic`: deterministic, useful for tests and smoke runs;
- `llm`: production extraction with model/config trace metadata.

Extractor output should include skipped reasons, not just units. This is
important because the narrow scope requires frequent intentional skips for
workspace-local content.

## 12. Ranking And Rendering

Ranking computes ordered evidence, not final truth.

Signals:

- query text relevance;
- recency;
- exact scope match;
- project-context match when present;
- event type;
- extraction confidence;
- historical read policy.

Rendering creates a compact evidence block:

```text
Relevant memory units:
- [2026-01-05] The user said they usually use pip.
- [2026-04-18, project=current] The user said this project should use uv and not pip.
```

Render output must preserve timestamps. Dialogue refs and other metadata labels
are optional renderer configuration.

Renderer evaluation should compare outputs after rendering, not before it. For a
fixed post-render token budget, prefer the algorithm that returns more relevant
fact units with adequate evidence, because that is the actual context the host
agent receives.

## 13. Maintenance Layer

Maintenance is engineering lifecycle work.

Jobs:

- retention expiration;
- hot/warm/cold tier transitions;
- index rebuild;
- index compaction;
- privacy redaction;
- idempotency record cleanup;
- trace cleanup.

Maintenance must not silently merge units or synthesize canonical user
profiles.

## 14. Admin And CLI Layer

Admin operations are control-plane operations for operators and future TUI
views. They are not part of the agent-facing memory API.

Initial admin service:

```python
class NanoMemAdminService:
    def stats(self) -> DatabaseStats:
        ...

    def list_units(
        self,
        scope: MemoryScope | None,
        time_range: TimeRange | None,
        limit: int | None,
    ) -> tuple[MemoryUnit, ...]:
        ...

    def list_operation_logs(
        self,
        scope: MemoryScope | None,
        operation_type: str | None,
        limit: int | None,
    ) -> tuple[OperationLogEntry, ...]:
        ...

    def reindex(self) -> ReindexResult:
        ...

    def retention_preview(self, policy: RetentionPolicy) -> RetentionPreview:
        ...

    def retention_apply(self, policy: RetentionPolicy) -> RetentionApplyResult:
        ...

    def operation_log_retention_preview(
        self,
        policy: OperationLogRetentionPolicy,
    ) -> OperationLogRetentionPreview:
        ...

    def operation_log_retention_apply(
        self,
        policy: OperationLogRetentionPolicy,
    ) -> OperationLogRetentionApplyResult:
        ...
```

The CLI and future TUI should call `NanoMemAdminService`. They should not issue
ad hoc SQL queries or mutate store/index internals directly.

Initial CLI commands:

```text
python -m nanomem.cli stats --db path/to/nanomem.sqlite3
python -m nanomem.cli migrations --db path/to/nanomem.sqlite3
python -m nanomem.cli integrity-check --db path/to/nanomem.sqlite3
python -m nanomem.cli backup --db path/to/nanomem.sqlite3 --output backup.sqlite3
python -m nanomem.cli export --db path/to/nanomem.sqlite3 --output export.json
python -m nanomem.cli maintenance-plan --config configs/nanomem.example.yaml
python -m nanomem.cli maintenance-run --config configs/nanomem.example.yaml --yes
python -m nanomem.cli list --db path/to/nanomem.sqlite3 --user-id user
python -m nanomem.cli logs --db path/to/nanomem.sqlite3 --type read
python -m nanomem.cli reindex --db path/to/nanomem.sqlite3
python -m nanomem.cli retention-preview --db path/to/nanomem.sqlite3 --before 2026-01-01
python -m nanomem.cli retention-apply --db path/to/nanomem.sqlite3 --before 2026-01-01 --yes
python -m nanomem.cli log-retention-preview --db path/to/nanomem.sqlite3 --before 2026-01-01 --type read
python -m nanomem.cli log-retention-apply --db path/to/nanomem.sqlite3 --before 2026-01-01 --type read --yes
python -m nanomem.cli dashboard --db path/to/nanomem.sqlite3
python -m nanomem.cli dashboard --db path/to/nanomem.sqlite3 --watch --interval 2
```

TUI starts as a dependency-free read-only terminal dashboard over the same admin
service. It can later grow into an interactive curses/textual interface without
changing the admin service contract.

- overview stats;
- user/tenant counts;
- recent capture/read operation logs;
- recent units;
- time-range filtered unit list;
- index freshness and reindex status;
- retention preview/apply status.

The first dashboard is not a full interactive UI. It is a dependency-free
terminal monitor that can render once or refresh in watch mode. The snapshot
includes:

- generation time;
- monitor status;
- index lag;
- database counts;
- recent operation logs with query, returned units, and response context;
- recent units;
- optional retention preview.

Admin responsibilities:

- operational inspection;
- stats and health summaries;
- unit listing for debugging;
- reindex orchestration;
- retention preview/apply;
- later privacy redaction/export.

Admin non-responsibilities:

- agent-facing capture/read behavior;
- semantic truth maintenance;
- workspace search;
- profile synthesis.

## 15. Server Layer

The server exposes HTTP endpoints for agent frameworks:

```text
POST /v1/capture
POST /v1/read
GET  /v1/health
```

Initial server startup:

```text
python -m nanomem.server --config configs/nanomem.example.yaml --host 127.0.0.1 --port 8765
```

Admin or maintenance endpoints may exist later, but they are not part of the
normal agent-facing API.

Server responsibilities:

- HTTP request parsing;
- async request handling;
- auth and tenant validation;
- request size limits;
- timeout handling;
- response serialization;
- structured request logging.

Server non-responsibilities:

- extraction logic;
- retrieval logic;
- storage semantics;
- truth resolution.
- admin, retention, or dashboard operations.

## 16. SDK And Adapters

The SDK is a thin typed HTTP client for `capture` and `read`:

```python
client = NanoMemClient("http://127.0.0.1:8765")
client.capture(CaptureRequest(...))
client.read(ReadRequest(...))
```

The async SDK is currently a standard-library wrapper around the same HTTP
client:

```python
client = AsyncNanoMemClient("http://127.0.0.1:8765")
await client.capture(CaptureRequest(...))
await client.read(ReadRequest(...))
```

Adapters translate host-agent lifecycle hooks into NanoMem requests.

OpenClaw-like integration:

```text
before_turn:
  NanoMem.read(...)

after_turn:
  NanoMem.capture(...)
```

`AgentMemoryAdapter` accepts any backend with the same two methods, so it can
run against an in-process `NanoMemService` or a remote `NanoMemClient`.
`OpenClawMemoryAdapter` and `NanoBotMemoryAdapter` are naming adapters over the
same hook contract rather than framework dependencies.

MCP integration is also an adapter, not a new product API. It exposes two tools:

```text
nanomem_capture
nanomem_read
```

MCP stdio startup:

```text
python -m nanomem.mcp --config configs/nanomem.example.yaml
```

The MCP adapter must not expose store, index, retention, export, backup, or TUI
operations as agent tools. Those remain admin/CLI responsibilities.

Adapters should not:

- read project files on behalf of the agent;
- build document indexes;
- resolve memory conflicts;
- call internal store or index classes directly.
- expose maintenance controls as agent tools.

## 17. Configuration

Recommended config groups:

```python
NanoMemConfig:
  capture: CaptureConfig
  read: ReadConfig
  store: StoreConfig
  index: IndexConfig
  extraction: ExtractionConfig
  render: RenderConfig
  maintenance: MaintenanceConfig
  server: ServerConfig
```

Result-affecting config should be recorded in traces and returned stats where
useful. Secret-bearing fields such as API keys and database passwords must not
appear in traces, responses, artifact ids, or cache keys.

Current startup config shape:

```yaml
data_dir: .nanomem

store:
  backend: sqlite

index:
  backend: dense
  metadata_filter_keys: []
  embedding:
    backend: hashing
    model: local-hash-128
    dimensions: 128

extraction:
  backend: heuristic

read:
  default_recency_policy: balanced
  default_max_units: 10

maintenance:
  integrity_check: true
  backup:
    enabled: false
    path: .nanomem/backups/nanomem.backup.sqlite3
    overwrite: false
  export:
    enabled: false
    path: .nanomem/exports/nanomem.export.json
    include_operation_logs: true
    overwrite: false
  retention:
    enabled: false
    max_age_days: 730
  operation_log_retention:
    enabled: false
    max_age_days: 90
```

If `store.path` is omitted, it defaults to `${data_dir}/nanomem.db`. A future
LanceDB adapter should similarly default to `${data_dir}/lancedb`.

OpenAI-compatible embedding config:

```yaml
index:
  backend: dense
  embedding:
    backend: openai_compatible
    model: text-embedding-3-small
    api_key_env: OPENAI_API_KEY
    base_url: null
```

OpenAI-compatible storage/extraction LLM config:

```yaml
extraction:
  backend: llm
  model: gpt-4.1-mini
  api_key_env: OPENAI_API_KEY
  base_url: null
  fallback_backend: heuristic
```

CLI commands may use either `--db` or `--config`:

```text
python -m nanomem.cli dashboard --config configs/nanomem.example.yaml
python -m nanomem.cli logs --config configs/nanomem.example.yaml --type read
python -m nanomem.cli stats --config configs/nanomem.example.yaml
python -m nanomem.cli migrations --config configs/nanomem.example.yaml
python -m nanomem.cli integrity-check --config configs/nanomem.example.yaml
python -m nanomem.cli maintenance-plan --config configs/nanomem.example.yaml
python -m nanomem.cli maintenance-run --config configs/nanomem.example.yaml --yes
python -m nanomem.cli reindex --config configs/nanomem.example.yaml
python -m nanomem.mcp --config configs/nanomem.example.yaml
```

## 18. Observability

Every `capture` and `read` should produce structured diagnostics.

Capture stats:

- accepted messages;
- skipped messages;
- extracted units;
- extractor name and model;
- latency;
- store/index write counts.

Read stats:

- resolved time range;
- candidate count;
- ranked count;
- returned unit count;
- context tokens;
- index backend;
- ranking policy;
- latency.

Trace records should help debug why NanoMem stored or returned personal
units without requiring raw workspace ingestion.

SQLite stores operation logs for both `capture` and `read`. Read logs include
the query, resolved time range, ranked unit ids/scores/text, and the rendered
context returned by NanoMem. These logs power the terminal dashboard and CLI
inspection without becoming part of the agent-facing memory API.

SQLite stores the database schema version in `PRAGMA user_version`. Admin stats
surface both the current schema version and the latest schema version known by
the running code. Migrations must be additive and explicit. Schema version `2`
adds a `schema_migrations` audit table plus scope/time indexes for operator
queries.

Operation logs have their own retention path. Unit retention deletes
MemoryUnits and rebuilds indexes; operation-log retention deletes only
diagnostic capture/read records and does not mutate MemoryUnits.

## 19. `memexp` Evaluation Adapter

`memexp` should evaluate NanoMem without becoming a dependency of NanoMem.

Two adapter modes are acceptable:

```text
in-process adapter:
  memexp -> nanomem.service.NanoMemService

server adapter:
  memexp -> nanomem.sdk.NanoMemClient -> NanoMem server
```

The server adapter is closer to production. The in-process adapter is useful
for deterministic tests and local experiments.

`memexp` remains responsible for:

- dataset conversion;
- experiment isolation;
- build/read replay;
- metrics;
- judge prompts;
- artifact writing.

NanoMem remains responsible for:

- capture and read semantics;
- storage and indexes;
- retention and redaction;
- production service behavior.

## 20. First Code Slice

The first implementation should be small enough to test end to end.

Files to implement first:

```text
src/nanomem/__init__.py
src/nanomem/contracts.py
src/nanomem/service/async_core.py
src/nanomem/service/core.py
src/nanomem/service/capture.py
src/nanomem/service/read.py
src/nanomem/extraction/base.py
src/nanomem/extraction/heuristic.py
src/nanomem/store/base.py
src/nanomem/store/sqlite.py
src/nanomem/index/base.py
src/nanomem/index/lexical.py
src/nanomem/ranking/ranker.py
src/nanomem/render/context.py
src/nanomem/admin/service.py
src/nanomem/cli/main.py
src/nanomem/tui/dashboard.py
src/nanomem/server/app.py
src/nanomem/server/schemas.py
src/nanomem/server/main.py
src/nanomem/serde.py
src/nanomem/sdk/client.py
src/nanomem/adapters/agent.py
src/nanomem/adapters/openclaw.py
src/nanomem/adapters/nanobot.py
```

First behavior:

1. capture user messages and explicit corrections;
2. extract simple personal units using a deterministic extractor;
3. append units to SQLite;
4. index unit text lexically;
5. read with owner/namespace filtering and recency-aware ranking;
6. return ranked units and rendered evidence context.
7. expose admin stats, list, and reindex through a CLI.
8. support retention preview/apply for engineering lifecycle cleanup.
9. render a read-only terminal dashboard from admin snapshots.
10. support dashboard watch mode for real-time operational monitoring.
11. expose minimal HTTP `/v1/health`, `/v1/capture`, and `/v1/read`.
12. expose a thin SDK and OpenClaw/NanoBot-style lifecycle adapters.

Do not expand adapters into agent framework responsibilities. They should map
turn hooks to NanoMem requests and leave workspace retrieval, planning, and
tool orchestration in the host agent.

## 21. Verification Strategy

Initial tests should cover:

- `capture` skips workspace-local content;
- `capture` appends personal units;
- `read` filters by user scope;
- `read` does not hard-filter old memories when `time_range` is omitted;
- `read` preserves timestamp in every rendered memory item;
- `read` returns evidence, not a canonical profile answer.
- async `capture` and `read` preserve the same semantics as sync calls;
- concurrent async calls do not corrupt capture or read behavior.
- admin stats report unit, dialogue, and operation-log counts;
- CLI JSON output is machine-readable for future TUI use;
- reindex rebuilds derived indexes from the authoritative store.
- retention preview reports expired units without mutation;
- retention apply requires explicit confirmation at the CLI and reindexes after deletion.
- dashboard output includes overview stats, recent units, and optional retention preview.
- dashboard watch mode refreshes repeated snapshots without mutating the store.
- HTTP server tests cover health, capture/read roundtrip, and invalid request handling.
- SDK tests cover typed HTTP capture/read roundtrip and server error handling.
- adapter tests cover before/after turn hooks without depending on agent frameworks.

Later integration tests should cover:

- HTTP server request/response compatibility;
- SDK compatibility;
- OpenClaw-like before/after turn hooks;
- `memexp` evaluation adapter behavior.
