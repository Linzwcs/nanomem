# Local MVP

Status: draft

The current local manager is a build-free browser app packaged inside
`nanomem.manager`. The existing NanoMem HTTP server mounts it without adding a
login layer.

```text
GET /manager              -> packaged manager index.html
GET /manager/assets/*.css -> packaged manager stylesheet
GET /manager/assets/*.js  -> packaged manager browser module
```

`/admin` remains a compatibility alias. The browser uses hash routes, so
server-side page routing is not required.

## Current Pages

- Overview dashboard.
- Memory Units list with filters and queue tabs.
- Full-page MemoryUnit detail route.
- Source evidence view resolved from `DialogueRef.message_range`.
- Operation Logs table.
- Retrieval Lab.
- Index Health with reindex action.

## Current Endpoints

```text
GET  /admin/api/stats
GET  /admin/api/memory-units
GET  /admin/api/memory-units/{unit_id}
GET  /admin/api/dialogues/{dialogue_id}
GET  /admin/api/operation-logs
POST /admin/api/reindex
POST /admin/api/retrieval-preview
```

## Current Data Path

```text
Browser UI
  -> Manager HTTP asset mount
  -> Admin HTTP API handlers
  -> NanoMemAdminService / NanoMemService
  -> SQLite authoritative store
  -> active MemoryUnitIndex
```

The UI reads authoritative memory and dialogue records from SQLite. Retrieval
preview calls the normal read pipeline. Reindex rebuilds the active index from
stored memory units.

## Immediate Gaps

- Pagination instead of fixed `limit` loading.
- Dedicated source endpoint for memory evidence.
- Raw dialogue reveal audit.
- Backup/export endpoints.
- Retention preview/apply endpoints.
- Delete/redact workflows.
- Authentication and role checks.
- Distinguishing admin preview read logs from runtime read logs.

## Development Constraint

Keep the MVP build-free until a frontend framework becomes necessary. If a
framework is introduced later, compiled assets should still be served under the
same `/admin/assets/*` path.
