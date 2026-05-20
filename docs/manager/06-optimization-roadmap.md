# Optimization Roadmap

Status: draft

The manager should stay simple while making room for larger memory stores
and stricter privacy workflows.

## Performance Optimizations

First priorities:

- paginated `memory-units` and `operation-logs`;
- indexed filters for owner, namespace, type, timestamp, and redaction;
- lazy loading of dialogue evidence;
- capped operation log payload display;
- retrieval preview rate limits;
- cached stats for large stores.

Avoid loading all dialogue content into the browser. Memory list pages should
load canonical units first and fetch source evidence only when a detail route is
opened.

## UI Optimizations

Improve review efficiency before adding complex visuals:

- persistent filters in the URL;
- keyboard-friendly table navigation;
- clear review queues: low confidence, missing evidence, redacted, stale index;
- compact badges for type, confidence, evidence status, and lifecycle state;
- copy buttons for stable ids;
- side-by-side view only when comparing retrieval outputs, not for normal unit
  detail.

Do not add knowledge graphs, animated timelines, or dashboard-heavy decoration
until the object model and workflows are proven.

## Service Refactor Path

As manager workflows grow, keep routing in `server/manager.py` and move larger
control workflows into focused modules:

```text
server/manager.py     -> routing and serialization
control/service.py    -> stats, integrity, maintenance use cases
control/evidence.py   -> DialogueRef -> source chunk resolution
control/operations.py -> preview/apply workflows
control/schemas.py    -> stable response dataclasses
```

Keep store interfaces focused on persistence primitives. Keep index interfaces
focused on `clear`, `upsert`, `search`, and `document_count`.

## Phases

Phase 1: read-only local console

- overview, memory list/detail, evidence, logs, retrieval lab, index health.

Phase 2: maintenance operations

- pagination, reindex history, backup, export, integrity check.

Phase 3: privacy operations

- retention preview/apply, redaction, raw reveal audit, role checks.

Phase 4: local deployment hardening

- localhost-by-default config, network exposure warnings, CSRF protection for
  state-changing local routes, audit trail, and deployment config.

Login authentication is intentionally out of scope for the current Manager
roadmap. If NanoMem later supports hosted multi-user deployments, that work
should be designed separately from the local-first management platform.
