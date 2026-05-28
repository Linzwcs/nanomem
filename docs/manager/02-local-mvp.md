# Local MVP

Status: active

The current local manager is a React/Vite browser app compiled into the
`nanomem.admin.manager_ui` package (`src/nanomem/admin/manager_ui/`). The
NanoMem HTTP server mounts those static assets without adding a login layer.

```text
GET /manager              -> packaged manager index.html
GET /manager/assets/*.css -> compiled manager stylesheet
GET /manager/assets/*.js  -> compiled manager browser module
```

`/admin` and `/admin/api/*` remain compatibility aliases that rewrite to the
`/manager` paths. The browser uses hash routes, so server-side page routing is
not required.

## Current Pages

- **Overview** — store + index health summary, top owner/namespace counts.
- **Sessions** — capture-stream list with window status badges; routeable
  detail page showing the ordered message stream + windows + produced units.
- **Dialogue Windows** — extraction-lifecycle list (open / sealed /
  extracted) with seal reason and produced unit count.
- **Memory Units** — review queue with collapsible filter strip (search,
  owner, namespace, type, time range, order); routeable detail page with
  fact card + lifecycle meta + source dialogue + metadata.
- **Retrieval Preview** — runtime-parity read simulator: compact form with
  Tuning disclosure, example-chip empty state, ranked table with R/T score
  breakdown, rendered context with Copy button.
- **Operations** — audit-log table with collapsible filters, single-line
  rows, status dot, summary chips capped with `+N` overflow.
- **Index Health** — 4 hero metric cards + backend details panel +
  ghost-tier Rebuild index action.

## Current Endpoints

```text
GET  /manager/api/stats
GET  /manager/api/sessions
GET  /manager/api/sessions/{session_id}
GET  /manager/api/dialogue-windows
GET  /manager/api/memory-units
GET  /manager/api/memory-units/{unit_id}
GET  /manager/api/dialogues/{dialogue_id}
GET  /manager/api/operation-logs
POST /manager/api/reindex
POST /manager/api/retrieval-preview
```

Backup, export, retention, redaction, and integrity-check operations are
CLI-only — see `03-control-api.md` for the boundary, and `05-operations-and-privacy.md`
for the privacy posture.

## Current Data Path

```text
Browser UI (React/Vite, hash-routed)
  -> Manager HTTP asset mount (/manager + /manager/assets/*)
  -> control-plane HTTP API handlers (/manager/api/*)
  -> ControlFacade -> NanoMemAdminService / NanoMemService.read()
  -> SQLite authoritative store
  -> active MemoryUnitIndex (derived)
```

The UI reads authoritative memory + dialogues from SQLite. Retrieval preview
calls the normal read pipeline. Reindex rebuilds the active index from stored
memory units.

## Immediate Gaps

- Dedicated source endpoint for memory evidence (today the detail endpoint
  returns full source chunks inline).
- Raw dialogue reveal endpoint with audit logging.
- Authentication and role checks for hosted deployment.
- Manager-vs-runtime read log distinction in the operation log.
- HTTP endpoints for the privacy/maintenance workflows that currently live
  only in the CLI (`backup`, `export`, `retention-*`).

## Development Constraint

The React source lives in `manager-ui/`. `npm run build` emits compiled assets
to `../src/nanomem/admin/manager_ui/` so the Python server keeps serving them
under `/manager/assets/*`. The Python deployment model does not change.
