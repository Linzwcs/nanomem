# Local MVP

Status: draft

The current local manager is a React/Vite browser app compiled into
`nanomem.manager.assets`. The existing NanoMem HTTP server mounts those static
assets without adding a login layer.

```text
GET /manager              -> packaged manager index.html
GET /manager/assets/*.css -> compiled manager stylesheet
GET /manager/assets/*.js  -> compiled manager browser module
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
GET  /manager/api/stats
GET  /manager/api/memory-units
GET  /manager/api/memory-units/{unit_id}
GET  /manager/api/dialogues/{dialogue_id}
GET  /manager/api/operation-logs
POST /manager/api/reindex
POST /manager/api/retrieval-preview
```

## Current Data Path

```text
Browser UI
  -> Manager HTTP asset mount
  -> control-plane HTTP API handlers
  -> NanoMemControlService / NanoMemService
  -> SQLite authoritative store
  -> active MemoryUnitIndex
```

The UI reads authoritative memory and dialogues from SQLite. Retrieval
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
- Distinguishing manager preview read logs from runtime read logs.

## Development Constraint

The React source lives in `manager-ui/`. Compiled assets must still be served
under the same `/manager/assets/*` path so the Python server and local
deployment model do not change.
