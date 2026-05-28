# Optimization Roadmap

Status: active

The manager should stay simple while making room for larger memory stores
and stricter privacy workflows.

## Performance Status

Shipped:

- paginated `memory-units`, `operation-logs`, `sessions`, `dialogue-windows`
  list endpoints (count / total_count / has_more);
- `placeholderData: keepPreviousData` on all list-page queries so filter
  inputs stay focused across refetches;
- collapsible filter strips so dense filter grids do not dominate the
  viewport when no filter is set;
- summary chip cap + `+N` overflow indicator in Operations (eliminates
  per-row height wobble);
- compact `MM/DD/YY HH:mm` time format for audit-log columns;
- single-line operation rows (~38px) for scan-heavy review;
- score breakdown stacked display (R / T sub-scores) in Retrieval Preview;
- Copy button on the Rendered Context block.

Next:

- indexed filters for owner, namespace, type, timestamp, redaction in
  the SQLite store (filters work today via WHERE clauses; add indexes
  once unit counts grow);
- lazy / streaming load of long dialogue evidence;
- capped operation log payload display in a detail route;
- retrieval preview rate limits;
- cached `stats` for large stores.

Avoid loading all dialogue content into the browser. Memory list pages
load canonical units first and fetch source evidence only when a detail
route is opened.

## UI Status

Shipped:

- persistent URL-backed filter state;
- collapsible filter strip with dismissable active-filter chips;
- copyable id chips for unit / dialogue / oplog ids;
- compact Badges for type, status, namespace, backend health;
- Retrieval Preview Use-example chips + Cmd/Ctrl+Enter submit;
- Operations status dot + summary `+N` overflow indicator;
- ghost-button-compact tier for low-priority page-header actions;
- example-chip empty state in Retrieval Preview.

Next:

- keyboard-friendly table navigation (j/k row stepping);
- review queues: missing evidence, redacted units, stale index;
- copy-as-curl for the Retrieval Preview request payload;
- side-by-side comparison only for retrieval backends, not for normal
  unit detail.

Do not add knowledge graphs, animated timelines, or dashboard-heavy
decoration until the object model and workflows are proven.

## Service Refactor Path

Routing and serialization live in `transports/http/manager.py`. Larger
control workflows belong in focused modules under `service/`:

```text
transports/http/manager.py    routing and JSON serialization
service/facade.py             ControlFacade for transports
service/admin_*.py            admin-only use cases (future split)
service/core.py / async_core  NanoMemService
```

Keep store interfaces focused on persistence primitives. Keep index
interfaces focused on `clear`, `upsert`, `search`, and `document_count`.

## Phases

Phase 1 (read-only local console): **done**.
Overview / Sessions / DialogueWindows / MemoryUnits / Retrieval / Operations
/ Index Health all ship with the React app.

Phase 2 (maintenance operations): **partial**.
Reindex ships through HTTP + CLI. Backup, export, integrity, retention live
in CLI only — re-introducing HTTP requires a UI design and a documented
consumer (see `03-control-api.md`).

Phase 3 (privacy operations): **not yet**.
Retention apply, redaction apply, raw reveal audit, role checks remain on
the roadmap.

Phase 4 (deployment hardening): **not yet**.
Localhost-by-default config, network exposure warnings, CSRF protection,
audit trail, deployment config.

Login authentication is intentionally out of scope for the current Manager
roadmap. If NanoMem later supports hosted multi-user deployments, that
work should be designed separately from the local-first management
platform.
