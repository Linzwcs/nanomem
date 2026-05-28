# Control API

Status: active

`/manager/api/*` is a control-plane API. It observes, diagnoses, and triggers
maintenance for the memory store. It must not redefine capture/read behavior or
duplicate ranking, rendering, or redaction logic.

`/admin/api/*` is a path alias that rewrites to `/manager/api/*`.

## Architecture

```text
/manager/api/*
  -> stdlib HTTP routing + JSON serialization (transports/http/manager.py)
  -> ControlFacade  (service/facade.py)
  -> NanoMemAdminService / NanoMemService.read()
  -> store (sqlite) / active index / read pipeline
```

HTTP handlers only parse inputs, call services, and serialize results. They
never reach into store/index internals.

## Endpoint Inventory

10 endpoints ship in the control plane today. The list below is authoritative
against `src/nanomem/transports/http/manager.py`.

### Observation

```text
GET /manager/api/stats
GET /manager/api/sessions
GET /manager/api/sessions/{session_id}
GET /manager/api/dialogue-windows
GET /manager/api/memory-units
GET /manager/api/memory-units/{unit_id}
GET /manager/api/dialogues/{dialogue_id}
GET /manager/api/operation-logs
```

All observation endpoints are read-only. List endpoints (`sessions`,
`dialogue-windows`, `memory-units`, `operation-logs`) accept `limit`, `offset`,
`page` and return `count` / `total_count` / `offset` / `limit` / `has_more` so
the UI can paginate.

`stats` includes index health fields for the active backend:

- `active_unit_count`: non-redacted MemoryUnits in the authoritative store;
- `index_document_count`: documents visible to the active index when supported;
- `index_health`: `synced`, `stale`, or `unknown`;
- `index_unit_delta`: `active_unit_count - index_document_count`;
- `last_reindex_at`: latest successful manager reindex operation timestamp;
- `top_owners`: top owner/namespace unit counts;
- optional `applied_schema_migration_count` / `pending_schema_migration_count`.

`memory-units` list supports:

- selectors: `owner_id`, `namespace`, `memory_type`, `start`, `end`, `text`;
- ordering: `newest_first` (default) or `oldest_first`.

`sessions` list supports `order` (`recently_updated` default).

`dialogue-windows` list supports `session_id`, `status`, `order`.

`operation-logs` list supports `owner_id`, `namespace`, `operation_type`,
`status`, `start`, `end`.

Time selector semantics:

- `memory-units.start` / `end` filter `MemoryUnit.timestamp`;
- `operation-logs.start` / `end` filter `OperationLog.created_at`;
- `retrieval-preview.time_range` hard-filters candidate `MemoryUnit.timestamp`;
- `retrieval-preview.query_time` is separate and only controls the
  recency-aware ranking policy.

The API accepts ISO timestamp strings. The browser manager exposes date-only
inputs but converts them into explicit ISO start/end boundaries before calling
the API. End dates are inclusive at the UI level and sent as the end of the
selected local day.

`memory-units/{unit_id}` returns the canonical `MemoryUnit` plus a derived
`source_chunks` field. Each chunk resolves a `DialogueRef` and includes:

- `status`: `ok`, `missing_dialogue`, `redacted_dialogue`, `empty_range`,
  or `out_of_range_clamped`;
- `range_label` and `resolved_range`;
- `message_count` and `resolved_message_count`;
- `raw_dialogue_available`;
- `messages` (full or range-resolved, depending on extractor).

`sessions/{session_id}` returns the session summary plus its dialogues,
windows, ordered stream messages, produced units, and operation logs.

### Diagnosis

```text
POST /manager/api/retrieval-preview
POST /manager/api/reindex
```

`retrieval-preview` calls `NanoMemService.read()` directly so the result matches
agent runtime behavior. The request payload exposes the same tuning controls
the runtime read accepts: `owner_id`, `namespaces`, `query`, `query_time`,
`time_range`, `max_units`, `context_budget_tokens`. The response includes
`ranked_units` (with `score`, `score_breakdown`, `unit`), `context`
(rendered text + token/unit counts), `stats` (candidate / ranked / rendered /
skipped counts, per-unit token estimates), and the resolved `request`.

`reindex` rebuilds derived index state from the authoritative store. The
response returns `indexed_unit_count`, `index_backend`, and supplemental
`stats`. Manager-triggered reindex writes an operation log entry with
operation type `reindex`.

## Out Of Scope For The HTTP Control Plane

Backup, export, retention preview/apply, and redaction are intentionally
**not** exposed over HTTP. They live in the `nanomem` CLI:

```text
nanomem backup            -> sqlite snapshot
nanomem export            -> JSON export of memory units / logs
nanomem retention-preview / retention-apply
nanomem log-retention-preview / log-retention-apply
nanomem integrity         -> schema + index consistency check
```

Rationale (recorded in CHANGELOG 0.3.0a5): the prior `MaintenanceService`
wrapper had no documented audience and no UI; operators wanting a scheduled
workflow chain these per-task CLI subcommands in their own cron script.
Re-introducing HTTP endpoints requires a documented control-plane consumer.

A future reveal endpoint for raw dialogue content (`POST
/manager/api/dialogues/{dialogue_id}/reveal`) remains on the privacy roadmap
behind permission + audit logging — see `05-operations-and-privacy.md`.
