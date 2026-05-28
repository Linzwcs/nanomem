# Web Management Console

Status: active

This document is the high-level product boundary for NanoMem's human-facing
management console inside the core NanoMem specs. Detailed UI, API, and
design specs live in `../manager/` — this file cross-links the manager docs
and keeps the cross-spec audit short.

The console is a control-plane product surface. It is not an agent-facing
memory interface and must not change the small `capture`/`read` API
boundary.

## 1. Purpose

NanoMem needs a web console because memory quality and privacy are hard to
judge from raw CLI output alone. Operators and developers need to inspect
what was stored, why it was stored, whether retrieval works, and whether
retention or redaction policies are behaving correctly.

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

It may show `MemoryUnit`, `Dialogue`, `DialogueWindow`, `Session`, and
`OperationLogEntry` records, but it must label their privacy level clearly.
Normal agent reads should continue to use `NanoMemService.read`.

## 3. Users And Permissions

The shipping single-operator model: local filesystem permissions are the
only gate. The HTTP control plane exposes inspection + retrieval preview +
reindex; everything else (backup, export, retention, redaction, integrity,
migrations) is a CLI subcommand.

Future hosted deployment role split — see
`../manager/00-control-plane-boundary.md`:

| Role | Purpose | Allowed Actions |
| --- | --- | --- |
| Viewer | inspect memory state | stats, list pages, retrieval preview |
| Operator | maintain local store | + reindex over HTTP; backup / export / retention via shell |
| Admin | privacy and destructive actions | + delete / redact / raw dialogue reveal (still shell-only today) |

For local sidecar use, a single local operator role is acceptable.

## 4. Information Architecture

Shipping top-level pages (see `../manager/01-information-architecture.md`
for detail):

```text
Overview
Sessions
Dialogue Windows
Memory Units
Retrieval Preview
Operations
Index Health
```

`Retention & Privacy`, `Backups & Exports`, and `Settings` from earlier
drafts are not implemented as pages — those workflows live in the CLI.

## 5. Current Local MVP

The console is a React 19 + Vite 8 app compiled from `manager-ui/` into the
`nanomem.admin.manager_ui` package. The existing NanoMem HTTP server serves
those static assets without adding a login layer:

```text
GET /manager              -> packaged manager index.html
GET /manager/assets/*.css -> compiled manager stylesheet
GET /manager/assets/*.js  -> compiled manager browser module
```

The browser app uses hash routes; no additional server-side page routes
are required. `/admin` and `/admin/api/*` remain compatibility aliases.

Implemented JSON endpoints (10 total, see `../manager/03-control-api.md`
for the full inventory):

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

Implemented pages — see `../manager/01-information-architecture.md` for
each page's structure. Highlights of the recent UI overhaul (v0.3.0a7):

- collapsible filter strips (auto-open when filters are present);
- `CopyableId` chips for unit / dialogue / oplog ids;
- Retrieval Preview redesign with Tuning disclosure, example-chip empty
  state, R/T score breakdown, Cmd+Enter submit, Copy context;
- Operations single-line rows with status dot and `+N` summary overflow;
- Memory Unit Detail dedup (full-width fact card, no redundant side
  table);
- Index Health Rebuild button downgraded to the compact ghost tier;
- search inputs keep focus across refetches
  (`placeholderData: keepPreviousData`).

Not yet implemented through HTTP / UI:

- backup / export / retention / redaction workflows (CLI only today);
- raw dialogue reveal endpoint with audit logging;
- authentication / authorization roles;
- manager-vs-runtime read distinction in operation logs.

## 6. Control-Plane API

The web console uses a control-plane API separate from `/v1/capture` and
`/v1/read`. Authoritative inventory is in `../manager/03-control-api.md`.

The API is implemented on top of `ControlFacade` and `NanoMemService.read()`
and does not duplicate storage or ranking logic.

`GET /manager/api/memory-units/{unit_id}` returns the canonical MemoryUnit
plus a derived `source_chunks` field. Each chunk resolves a `DialogueRef`
into the referenced dialogue metadata. The default source is the whole
dialogue; when a future extractor provides a non-null `message_range`, the
manager uses it only as a highlight inside that dialogue. This keeps the
browser simple while preserving `MemoryUnit` as the canonical stored fact.

Each source chunk includes:

- `status`: `ok`, `missing_dialogue`, `redacted_dialogue`, `empty_range`,
  or `out_of_range_clamped`;
- `range_label`: `Full dialogue` or a human-readable original
  `DialogueRef.message_range`;
- `resolved_range`: actual message range after bounds resolution;
- `message_count` and `resolved_message_count`;
- `raw_dialogue_available`.

Destructive endpoints (when added) must require:

- explicit confirmation field;
- scoped filters;
- dry-run / preview support;
- operation log entry.

## 7. Architecture

Shipping topology:

```text
React/Vite browser UI (hash-routed)
  -> control-plane HTTP API (transports/http/manager.py)
  -> ControlFacade  (service/facade.py)
  -> NanoMemAdminService / NanoMemService.read()
  -> SQLite fact store
  -> active MemoryUnitIndex
```

For local development, the console is served by the same process as the
control-plane API. For hosted deployments, serve it behind normal
authentication and do not expose raw dialogue endpoints publicly.

The UI treats the index as cache-like derived state. It can display index
health, but all authoritative data comes from the store.

## 8. MVP Scope

Shipping MVP (Phase 1 + partial Phase 2 — see
`../manager/06-optimization-roadmap.md`):

1. Overview dashboard.
2. Sessions list + detail (chronological stream + window overlay).
3. Dialogue Windows list.
4. MemoryUnit full-width list with routeable detail page.
5. Dialogue evidence panel inside MemoryUnit detail.
6. Operation log table.
7. Retrieval Preview.
8. Index Health with reindex button.

Explicitly deferred:

- editing MemoryUnit text;
- HTTP backup / export / retention / redaction workflows;
- multi-tenant auth;
- persistent vector index management;
- charts beyond basic counts;
- raw multimodal asset previews.

## 9. UX Principles

- Show dense tables, not marketing cards.
- Keep timestamps visible on every memory row.
- Make owner and namespace filters persistent in the URL.
- Use badges for memory type, namespace, redaction, retention status; use
  9px status dots in tight columns where a Badge wastes width.
- Require explicit user action before showing raw Dialogue content.
- Highlight skipped capture reasons.
- Show when rendered context differs from ranked hits due to token
  budget (Retrieval Preview kept-vs-cut row styling).
- Drop empty detail panels rather than render an empty card.

## 10. Privacy Defaults

Default behavior:

- bind to localhost unless configured otherwise;
- require auth before network exposure;
- hide raw Dialogue content until explicitly opened;
- do not show secrets from config;
- do not include raw personal content in browser console logs;
- do not expose manager/control endpoints through MCP or agent adapters.

## 11. Open Design Questions

- Should manual MemoryUnit insertion exist as a manager feature, or should
  all new memories go through capture evidence?
- Should the console support approving candidate extractions before
  storage?
- Should retention apply delete Dialogues independently from MemoryUnits?
- Should Retrieval Preview support side-by-side backend comparison?

## 12. Implementation Plan

Phase 1 (read-only local console): **done**.
Phase 2 (maintenance operations): **partial** — reindex over HTTP +
CLI; backup / export / retention / integrity are CLI-only.
Phase 3 (privacy operations): retention apply, redaction, raw reveal
audit — not yet.
Phase 4 (deployment hardening): authentication, authorization, CSRF
protection, audit log — not yet.
