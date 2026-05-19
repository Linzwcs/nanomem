# Index Backends

Status: draft

NanoMem keeps retrieval simple in the core package. It does not implement ANN
algorithms internally. ANN-capable retrieval should be delegated to database
backends through the `MemoryUnitIndex` adapter boundary.

## 1. Backend Strategy

```text
small local / tests:
  in-memory lexical, dense, or hybrid

local persistent ANN:
  SQLite fact store + LanceDB vector index
  data_dir = .nanomem

managed / multi-user:
  Postgres fact store + pgvector index
```

The service layer always talks to the same interface:

```python
class MemoryUnitIndex:
    def clear(self) -> None: ...
    def upsert(self, units: tuple[MemoryUnit, ...]) -> None: ...
    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]: ...
    def delete(self, unit_ids: tuple[str, ...]) -> None: ...
```

## 2. In-memory Baseline

Current backends:

- `dense`: default bounded embedding retrieval after owner/namespace filtering;
- `lexical`: deterministic token-overlap fallback and debugging baseline;
- `hybrid`: merge of lexical and dense scores.

The local dense index uses `index.dense_scan_limit` to cap per-query similarity
work. It is useful for smoke runs, tests, and small local memories. It is not an
ANN index and should not grow into one.

## 3. LanceDB Adapter

Use LanceDB when NanoMem runs as a local sidecar and needs persistent vector
retrieval without a separate server.

Recommended split:

```text
SQLiteMemoryUnitStore = .nanomem/nanomem.db
LanceDBMemoryUnitIndex = .nanomem/lancedb
```

Use a single NanoMem data directory so local state can be backed up, moved, or
deleted as one unit.

The LanceDB table should duplicate only the metadata required for search-time
filtering:

```text
unit_id
owner_id
namespace
tags / metadata filters
timestamp / available_at
retrieval_text
embedding_model
embedding
```

The store remains authoritative. The LanceDB index must be rebuildable from
stored MemoryUnits.

## 4. Postgres + pgvector

Use Postgres + pgvector when NanoMem becomes a managed or multi-user service and
needs stronger concurrency, metadata filtering, backup, retention, audit, and
permissions.

Recommended split:

```text
PostgresMemoryUnitStore = durable facts and operation metadata
PgVectorMemoryUnitIndex = vector index table in the same Postgres deployment
```

This path is heavier than SQLite and is not the default local setup. It becomes
appropriate when operational controls matter more than zero-service deployment.

## 5. What Not To Do

Do not:

- store vectors as JSON in SQLite and scan all rows;
- implement HNSW/IVF/PQ inside NanoMem core;
- let `NanoMemService` depend on LanceDB, pgvector, or any concrete backend;
- make the vector index the source of truth for MemoryUnits;
- mix embedding dimensions in one vector table.

## 6. Selection Guide

| Scenario | Fact store | Index backend |
| --- | --- | --- |
| Unit tests | in-memory or SQLite | dense / lexical |
| Local single-user sidecar | SQLite | dense / hybrid |
| Local sidecar with persistent ANN | SQLite | LanceDB adapter |
| Managed multi-user service | Postgres | pgvector adapter |
