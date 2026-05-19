# Index Backends

Status: draft

This document defines NanoMem's retrieval backend strategy.

## 1. Purpose

Indexes accelerate candidate retrieval. They are not the source of truth and
must be rebuildable from stored MemoryUnits.

NanoMem core should not implement ANN algorithms. ANN-capable retrieval belongs
behind `MemoryUnitIndex` adapters.

## 2. Interface

```python
class MemoryUnitIndex:
    def clear(self) -> None: ...
    def upsert(self, units: tuple[MemoryUnit, ...]) -> None: ...
    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]: ...
    def delete(self, unit_ids: tuple[str, ...]) -> None: ...
```

`IndexSearchRequest` should include owner, namespaces, query text or vector,
time range, and candidate limit. The index may return approximate candidates;
the store and ranker enforce final behavior.

## 3. First-Version Backends

Current local backends:

- `dense`: default bounded embedding retrieval after owner/namespace filtering;
- `lexical`: deterministic token fallback over MemoryUnit text;
- `hybrid`: merge of lexical and dense scores.

`dense` must use `index.dense_scan_limit` or equivalent to cap per-query
similarity work. It is a baseline, not an ANN system.

## 4. LanceDB

Use LanceDB when a local sidecar needs persistent vector search without running
a server.

Recommended layout:

```text
SQLiteMemoryUnitStore = .nanomem/nanomem.db
LanceDBMemoryUnitIndex = .nanomem/lancedb
```

The LanceDB table may duplicate only search-time fields:

```text
unit_id
owner_id
namespace
timestamp
available_at
memory_type
retrieval_text
embedding_model
embedding
metadata filters selected by config
```

The authoritative MemoryUnit remains in SQLite. LanceDB must be rebuildable from
the fact store. Arbitrary `metadata` must not be indexed by default; only
configured filter keys may be duplicated into backend-specific columns.

## 5. Postgres + pgvector

Use Postgres + pgvector only when deployment requirements justify a managed
database:

- multi-user service;
- concurrency beyond local sidecar needs;
- central backup and retention policy;
- audit controls;
- metadata filtering in one operational database.

Recommended split:

```text
PostgresMemoryStore = facts, dialogue records, logs
PgVectorMemoryUnitIndex = vector table or indexed column
```

This is not the default local setup.

## 6. What Not To Do

Do not:

- store vectors as JSON in SQLite and scan all rows;
- implement HNSW, IVF, PQ, or other ANN algorithms in NanoMem core;
- let service code depend on LanceDB or pgvector types;
- let the vector index become authoritative for MemoryUnit text;
- mix embedding dimensions or embedding models in one unversioned index.

## 7. Selection Guide

| Scenario | Fact store | Index backend |
| --- | --- | --- |
| Unit tests | in-memory or SQLite | dense / lexical |
| Local single-user sidecar | SQLite | dense / hybrid |
| Local sidecar with persistent ANN | SQLite | LanceDB |
| Managed multi-user service | Postgres | pgvector |

The service layer should not care which backend is selected.
