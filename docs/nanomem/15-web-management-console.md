# Web Management Console

Status: draft

This document defines a web management platform for observing and operating
NanoMem memory stores. The console is a control-plane product surface. It is
not an agent-facing memory interface and must not change the small
`capture`/`read` API boundary.

Detailed manager design now lives in `../manager/`. This document remains
the high-level product boundary inside the core NanoMem specs.

## 1. Purpose

NanoMem needs a web console because memory quality and privacy are hard to
judge from raw CLI output alone. Operators and developers need to inspect what
was stored, why it was stored, whether retrieval works, and whether retention
or redaction policies are behaving correctly.

The console should answer:

- What memories exist for an owner and namespace?
- Which dialogue evidence produced a MemoryUnit?
- What was skipped during capture and why?
- Is the active index fresh relative to the authoritative store?
- What would retention or export operations affect?
- Are there suspicious or low-quality extracted memories?

## 2. Product Boundary

The console is for humans managing memory. It should not become:

- a chat UI;
- a general document browser;
- a replacement for local workspace search;
- an agent plugin surface;
- an all-in-one memory editing tool for arbitrary files, logs, or assets.

It may show `MemoryUnit`, `Dialogue`, and `OperationLogEntry` records, but
it must label their privacy level clearly. Normal agent reads should continue to
use `NanoMem.read`.

## 3. Users And Permissions

First-version roles:

| Role | Purpose | Allowed Actions |
| --- | --- | --- |
| Viewer | inspect memory state | stats, list, search preview, read logs |
| Operator | maintain local store | reindex, backup, export, retention preview |
| Admin | privacy and destructive actions | retention apply, delete, redact, raw dialogue inspection |

For local sidecar use, a single local operator role is acceptable. For hosted
deployments, role separation is required before exposing the console over a
network.

## 4. Information Architecture

Recommended top-level pages:

```text
Overview
Memory Units
Dialogue Evidence
Operation Logs
Retrieval Lab
Index Health
Retention & Privacy
Backups & Exports
Settings
```

### Overview

Shows operational health:

- store backend and path;
- schema version and pending migrations;
- unit, owner, namespace, dialogue, and operation log counts;
- active index backend and document count;
- index lag: `store unit_count - index_document_count`;
- oldest/newest MemoryUnit timestamps;
- top owner/namespace pairs.

This page maps directly to `NanoMemControlService.stats()`.

### Memory Units

Primary memory browser.

Filters:

- owner id;
- namespace list;
- memory type;
- time range;
- redaction state;
- free-text search preview.

Columns:

- timestamp;
- owner;
- namespace;
- memory type;
- short text;
- dialogue ref count;
- retention/redaction state.

Actions:

- inspect unit detail;
- copy unit id;
- open evidence dialogue;
- preview delete/redact;
- run retrieval test using the unit text.

Editing MemoryUnit text should not be part of v1. If correction is needed, add
new evidence through capture or use explicit control-plane redaction/delete.

### Dialogue Evidence

Control-plane evidence browser. This page should be gated because it contains
raw user-visible dialogue.

Views:

- dialogue metadata;
- message list with role, speaker_id, timestamp, and content;
- MemoryUnits produced from each message range;
- checksum and lifecycle fields;
- retention/redaction state.

Dialogue must not be included in normal agent read results. The console
may inspect it only for audit, debugging, and privacy operations.

### Operation Logs

Operational trace view.

Filters:

- operation type: capture, read, reindex, retention, export, backup;
- owner/scope when available;
- status;
- created_at range.

Use cases:

- see recent capture/read activity;
- inspect skipped capture reasons;
- diagnose why a read returned too few memories;
- confirm retention or reindex operations.

Operation logs should avoid raw personal content where possible. The UI should
prefer summaries and ids.

### Retrieval Lab

Interactive read debugger for developers and operators.

Inputs:

- owner id;
- namespace list;
- query;
- query_time, defaulting to current UTC time when omitted in the manager preview;
- time_range;
- recency_policy;
- max_units;
- context_budget_tokens.

Outputs:

- ranked units;
- score breakdown;
- rendered context;
- index backend;
- candidate/ranked/returned counts.

This page may call the same read pipeline, but it is an operator diagnostic
surface, not an agent tool. It should clearly mark that results are previews.

### Index Health

Shows derived-index state:

- active backend;
- document count;
- store unit count;
- index lag;
- embedding model name;
- dense scan limit;
- last reindex operation;
- reindex preview and run action.

Important behavior:

- SQLite is authoritative.
- Dense, lexical, hybrid, LanceDB, and pgvector indexes are derived.
- Reindex rebuilds from store and should be safe to repeat.

### Retention & Privacy

Human-facing privacy controls.

Workflows:

- retention preview;
- retention apply with confirmation;
- owner export;
- redaction preview;
- delete/redact apply;
- raw dialogue export only with explicit mode.

Destructive operations must show:

- matched record counts;
- sample affected records;
- owner/namespace filters;
- whether reindex will run afterward;
- irreversible action warning.

### Backups & Exports

Operational data movement.

Actions:

- create SQLite backup;
- create logical JSON export;
- list recent backup/export operations;
- show generated file paths and sizes.

Exports should distinguish:

- MemoryUnit-only export;
- MemoryUnit + operation log export;
- raw Dialogue export.

Raw Dialogue export should be disabled by default.

## 5. Current Local MVP

The current implementation serves a dependency-free local console from packaged
browser assets in the existing HTTP server:

```text
GET /manager              -> packaged manager index.html
GET /manager/assets/*.css -> packaged manager stylesheet
GET /manager/assets/*.js  -> packaged manager browser module
```

The browser app uses hash routes, so no additional server-side page routes are
required.

`/admin` remains a compatibility alias. JSON control-plane endpoints continue
to live under `/manager/api/*`.

Implemented JSON endpoints:

```text
GET  /manager/api/stats
GET  /manager/api/memory-units
GET  /manager/api/memory-units/{unit_id}
GET  /manager/api/dialogues/{dialogue_id}
GET  /manager/api/operation-logs
POST /manager/api/reindex
POST /manager/api/retrieval-preview
```

Implemented pages:

- overview dashboard;
- MemoryUnit review workspace with a full-width list and routeable detail page;
- owner, namespace, memory type, date range, redaction, order, and limit
  filters for MemoryUnits;
- full-page source evidence view resolved from `DialogueRef.message_range`;
- Dialogue evidence lookup from unit refs;
- operation log table;
- retrieval preview lab;
- index health and reindex action.

Not yet implemented:

- backup/export buttons;
- retention preview/apply;
- delete/redact workflows;
- authentication/authorization;
- raw dialogue access audit.
- separate reveal/audit API for raw dialogue messages.

## 6. Control-Plane API

The web console should use a control-plane API separate from `/v1/capture` and
`/v1/read`.

Suggested endpoints:

```text
GET  /manager/api/stats
GET  /manager/api/memory-units
GET  /manager/api/memory-units/{unit_id}
GET  /manager/api/dialogues/{dialogue_id}
GET  /manager/api/operation-logs
POST /manager/api/reindex
POST /manager/api/retention/preview
POST /manager/api/retention/apply
POST /manager/api/backup
POST /manager/api/export
POST /manager/api/retrieval-preview
```

The API should be implemented on top of `NanoMemControlService`,
`NanoMemService.reindex`, and existing store selectors. It should not duplicate
storage or ranking logic.

`GET /manager/api/memory-units/{unit_id}` may return a derived `source_chunks`
field for the console. Each chunk resolves a `DialogueRef` into the referenced
dialogue metadata. The default source is the whole dialogue; when a future
extractor provides a non-null `message_range`, the manager uses it only as a
highlight inside that dialogue. This keeps the browser simple while preserving
`MemoryUnit` as the canonical stored fact.

Each source chunk should include:

- `status`: `ok`, `missing_dialogue`, `redacted_dialogue`, `empty_range`, or
  `out_of_range_clamped`;
- `range_label`: `Full dialogue` or a human-readable original
  `DialogueRef.message_range`;
- `resolved_range`: actual message range after bounds resolution;
- `message_count` and `resolved_message_count`;
- `raw_dialogue_available` and `requires_explicit_reveal` for privacy-aware UI.

Destructive endpoints should require:

- explicit confirmation field;
- scoped filters;
- dry-run/preview support;
- operation log entry.

## 7. Architecture

Recommended first implementation:

```text
Packaged browser UI
  -> control-plane HTTP API
  -> NanoMemControlService / NanoMemService
  -> SQLite fact store
  -> active MemoryUnitIndex
```

For local development, the console can be served by the same process as the
control-plane API. For hosted deployments, serve it behind normal authentication and do
not expose raw dialogue endpoints publicly.

The UI must treat the index as cache-like derived state. It can display index
health, but all authoritative data should come from the store.

The local browser UI should stay build-free until there is a strong need for a
front-end toolchain. Prefer packaged `index.html`, `styles.css`, and browser
modules over large Python string templates. If React, Svelte, or Vite is added
later, the built assets should still be served from the same `/manager/assets/*`
surface.

## 8. MVP Scope

Recommended MVP:

1. Overview dashboard.
2. MemoryUnit full-width list with routeable detail page.
3. Dialogue evidence page section from `DialogueRef`.
4. Operation log table.
5. Retrieval Lab.
6. Index Health with reindex button.

Explicitly defer:

- editing MemoryUnit text;
- destructive delete/redact UI;
- multi-tenant auth;
- persistent vector index management;
- charts beyond basic counts;
- raw multimodal asset previews.

## 9. UX Principles

- Show dense tables, not marketing cards.
- Keep timestamps visible on every memory row.
- Make owner and namespace filters persistent.
- Use badges for memory type, namespace, redaction, and retention status.
- Require explicit user action before showing raw Dialogue content.
- Highlight skipped capture reasons.
- Show when rendered context differs from ranked hits due to token budget.

## 10. Privacy Defaults

Default behavior:

- bind to localhost unless configured otherwise;
- require auth before network exposure;
- hide raw Dialogue content until explicitly opened;
- do not show secrets from config;
- do not include raw personal content in browser console logs;
- do not expose manager/control endpoints through MCP or agent adapters.

## 11. Open Design Questions

- Should manual MemoryUnit insertion exist as a manager feature, or should all
  new memories go through capture evidence?
- Should the console support approving candidate extractions before storage?
- Should retention apply delete Dialogues independently from MemoryUnits?
- Should Retrieval Lab support side-by-side backend comparison?

## 12. Implementation Plan

Phase 1: read-only local console

- control stats endpoint;
- memory unit list/detail;
- dialogue evidence lookup;
- operation log list;
- retrieval preview.

Phase 2: maintenance operations

- reindex;
- backup;
- export;
- retention preview.

Phase 3: privacy operations

- retention apply;
- redaction;
- owner delete/export workflows;
- raw dialogue access audit.

Phase 4: deployment hardening

- authentication;
- authorization roles;
- CSRF protection;
- audit log;
- hosted deployment settings.
