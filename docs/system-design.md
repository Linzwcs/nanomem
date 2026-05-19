# NanoMem System Design

Status: draft

This document is the top-level design entry point for NanoMem. It connects the
product boundary, memory model, capture/read flows, storage/index strategy,
configuration, operations, and roadmap.

The modular design specs live under `docs/nanomem/`.

## 1. Product Boundary

NanoMem is a long-term personal memory database for agents. It is not an
all-in-one memory layer, workspace search engine, document store, skill store,
task database, or raw event log.

Modern agent harnesses can already read local files, search repos, inspect git,
run commands, read logs, and call tools. NanoMem should only manage durable
personal memory that does not naturally belong in the workspace:

- preferences;
- corrections;
- habits;
- personal background;
- relationship facts;
- user-relevant events;
- agent-interaction events that affect future collaboration.

## 2. Memory Model

NanoMem uses four distinct layers:

```text
DialogueRecord  = archived user-visible dialogue evidence
MemoryUnit      = fine-grained durable personal fact
IndexHit        = derived retrieval candidate
PackedContext   = rendered evidence for the agent prompt
```

User-visible dialogue is the capture source. MemoryUnits are the storage unit.
Indexes are derived data and must be rebuildable. Rendered context is the final
agent input.

MemoryUnits should be third-person and evidence-grounded:

```text
The user said they prefer concise Chinese answers.
The user corrected the agent not to auto-commit code.
The agent auto-committed code and the user reacted negatively.
```

Avoid first-person notes and direct command-like memories unless the statement
itself records that the user gave an instruction.

## 3. Capture Pipeline

```text
CaptureRequest
  -> validate scope and dialogue
  -> archive DialogueRecord
  -> normalize user-visible dialogue
  -> chunk = n for extraction
  -> annotate speaker/role
  -> extract third-person personal facts
  -> apply quality gates and skip reasons
  -> append MemoryUnits to store
  -> update derived index
  -> record operation log
```

Capture must not ingest hidden reasoning, tool calls, tool results, complete
chat archives, project documents, raw multimodal assets, or current task logs.

## 4. Read Pipeline

```text
ReadRequest
  -> resolve owner, namespaces, and explicit time filter
  -> retrieve candidate MemoryUnits through index
  -> load authoritative units from store
  -> rank by relevance, recency, namespace, confidence, and policy
  -> render evidence under post-render token budget
  -> record operation log
```

Read returns evidence, not a canonical user profile. Conflicting facts should be
rendered with timestamps so the downstream agent can reason over time.
Additional labels such as dialogue refs, namespace, confidence, tags, and
project hints are renderer configuration.

## 5. Storage And Indexing

Default local layout:

```text
.nanomem/
  nanomem.db
  lancedb/
  backups/
  exports/
```

Current implemented path:

```text
SQLiteMemoryUnitStore
lexical / bounded dense / hybrid in-memory indexes
```

Planned extension paths:

```text
SQLite fact store + LanceDB vector index
Postgres fact store + pgvector index
```

NanoMem should not implement ANN internally. ANN belongs behind
`MemoryUnitIndex` adapters. SQLite remains the default fact store and should not
be turned into a JSON-vector scanning engine.

## 6. APIs And Integrations

The external API remains small:

```text
capture
read
```

Integration pattern:

```text
before_turn:
  agent reads workspace/tools
  agent calls NanoMem.read for personal evidence

after_turn:
  agent sends user-visible dialogue to NanoMem.capture
```

Agent adapters must not expose admin, backup, export, retention, or raw index
operations as agent tools.

## 7. Configuration

Current local config shape:

```yaml
data_dir: .nanomem

scope:
  default_namespace: personal
  allowed_namespaces:
    - personal
    - work
    - research

store:
  backend: sqlite

index:
  backend: hybrid
  dense_scan_limit: 2000
  metadata_filter_keys: []
  embedding:
    backend: hashing
    dimensions: 128

extraction:
  backend: heuristic

read:
  default_recency_policy: balanced
  default_max_units: 10
```

If `store.path` is omitted, it defaults to `${data_dir}/nanomem.db`. A future
LanceDB adapter should default to `${data_dir}/lancedb`.

Capture writes to one namespace. Read defaults to all allowed namespaces for the
owner unless the caller provides a narrower namespace list.

## 8. Operations And Privacy

NanoMem stores personal data. Operational support must include:

- integrity checks;
- physical SQLite backup;
- logical JSON export;
- operation log retention;
- MemoryUnit retention;
- reindex from authoritative store;
- future privacy delete/redaction.

Raw source files, raw multimodal assets, logs, and workspace artifacts should
remain outside NanoMem. If auditability is needed, store a separate
`DialogueRecord` and put host log pointers in metadata; do not expose raw
resources as normal memory evidence.

## 9. Roadmap

Phase 0: design freeze

- finalize product boundary and MemoryUnit style;
- define capture/read pipelines and storage/index strategy;
- align README and docs.

Phase 1: SQLite local core stabilization

- add focused tests for store, capture, read, ranking, rendering, and CLI;
- keep local index simple and bounded;
- harden `data_dir` behavior.

Phase 2: extraction quality

- enforce third-person evidence style;
- improve memory type classification;
- add speaker/role-scoped extraction tests.

Phase 3: LanceDB adapter

- add optional dependency;
- implement `LanceDBMemoryUnitIndex`;
- add rebuild/reindex tests.

Phase 4: API and integration hardening

- document HTTP, SDK, MCP request/response examples;
- add smoke tests;
- clarify agent harness lifecycle.

Phase 5: managed deployment path

- evaluate Postgres + pgvector only when multi-user, server-side deployment
  requirements justify the operational complexity.
