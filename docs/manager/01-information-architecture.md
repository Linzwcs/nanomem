# Information Architecture

Status: active

The manager is organized around the user-visible memory flow and the links
between stored objects. Dialogue chunks are implementation evidence for
extraction; the human-facing raw view is the ordered session message stream.

```text
Overview
Sessions
Dialogue Windows
Memory Units
Retrieval Preview
Operations
Index Health
```

These seven sections match the shipped sidebar in `components/Shell.tsx`.
There is no "Retention & Privacy", "Backups & Exports", or "Settings"
section — those workflows live in the CLI today (see `03-control-api.md`).

## Overview

Hero block plus secondary metric cards. Shows store + index health at a
glance:

- active memory unit count across owners and namespaces;
- store backend, path (mono chip), schema version + pending migrations;
- session / dialogue / open-window / indexed-document counts;
- index lag: `store unit_count - index_document_count`;
- top owner/namespace pairs.

## Sessions

The main debugging entry point for agent integrations. The list shows one
row per session with open / sealed / extracted / failed window-status
chips, total message count, produced unit count, and updated time. The
detail page shows the chronological message stream first and overlays
DialogueWindow boundaries on top of it — not split by Dialogue id.

## Dialogue Windows

The operational view of extraction buffering. Answers why a capture did
or did not produce MemoryUnits. Rows show session id, dialogue id (copyable
chip), status, message count, token count, seal reason, produced unit
count, updated time.

## Memory Units

The primary review workspace. Dense full-width table for scanning and a
routeable detail page for investigation. Filter strip collapses by default
and auto-opens when the URL has active filters.

Filters: text search, owner id, namespace, memory type, time range, order
(`newest_first` default), page size.

Rows: short memory text + copyable unit id, scope (owner / namespace),
memory type badge, source dialogue ref count, timestamp.

Detail: status chip strip + timestamp, full-width fact card with copyable
unit id + meta grid (owner / namespace / available at / source +
optional retention until / redacted at), source dialogue panel with
status + range + messages, metadata block (only when non-empty).

## Retrieval Preview

Runtime-parity read simulator. Calls the real read pipeline through
`POST /manager/api/retrieval-preview`.

Form:
- primary row: Owner / Namespaces / Use example / Run preview;
- Query textarea (Cmd/Ctrl+Enter to submit);
- Tuning `<details>` disclosure for Budget tokens / Max units / Query
  time / TimeRange — collapsed by default with a summary chip showing
  current settings.

Empty state: "Try a query" panel with up to three example chips sampled
from real stored units (one chip per distinct owner/namespace). Clicking
a chip prefills and auto-runs.

Results:
- 4 metric cards: candidate / ranked / rendered / skipped counts.
- Ranked table with 4 columns: rank, memory (text + timestamp +
  namespace), score (overall + R + T sub-scores from
  `score_breakdown`), tokens (estimate + "cut" pill when skipped).
  Kept rows get a green left bar, cut rows render dimmed.
- Rendered Context panel: budget chip + Copy button + the rendered text.

Two distinct time controls live in the Tuning disclosure: `query_time`
(simulated current time for recency ranking) and `memory time range`
(hard filter over MemoryUnit evidence timestamps).

## Operations

Audit log with collapsible filters. Single-line rows for high scan
density:

- compact time (`MM/DD/YY HH:mm`);
- operation type + copyable oplog id chip inline;
- status as a 9px colored dot (green / red / amber);
- scope inline as `owner · namespace`;
- summary chips capped at 3 with `+N` overflow indicator.

Filters: operation type, status, owner, namespace, time range, row limit.

## Index Health

4 hero metric cards (active units / index documents / delta / backend) and
a Backend details panel that only shows fields not already in the cards
(e.g. embedding model, dense scan limit).

The Rebuild index action uses the compact ghost button tier so it does not
compete with the page title or the synced/stale badge.

## Navigation Model

Object links remain explicit:

```text
query -> ranked MemoryUnit -> DialogueRef -> Dialogue -> OperationLog
```

For manager UX:

```text
Session message stream -> DialogueWindow overlay -> produced MemoryUnit
MemoryUnit -> DialogueRef -> source Dialogue -> optional highlighted messages
```

Every object has a stable hash-route URL and a copyable id chip. Detail
pages prefer links over packing everything into one page.
