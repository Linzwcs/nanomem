# Information Architecture

Status: draft

The manager should be organized around the user-visible memory flow and the
links between stored objects. Dialogue chunks are implementation evidence for
extraction; the human-facing raw view is the ordered session message stream.

```text
Overview
Sessions
Dialogue Windows
Memory Units
Operation Logs
Retrieval Lab
Index Health
Retention & Privacy
Backups & Exports
Settings
```

## Overview

Shows store and index health:

- store backend, path, schema version, migration status;
- memory unit, owner, namespace, dialogue, and operation log counts;
- active index backend and indexed document count;
- index lag: `store unit_count - index_document_count`;
- oldest and newest memory timestamps;
- top owner/namespace pairs.

## Sessions

The main debugging entry point for agent integrations. A session page should
show one chronological message stream and overlay extraction windows on top of
that stream.

Rows or sections should show:

- session id and latest capture time;
- open, sealed, extracted, and failed window counts;
- total message count;
- produced memory count;
- latest operation.

The session detail page should not split the user's view by Dialogue ids first.
It should show messages in order, then mark which DialogueWindow/chunk processed
which message range.

## Dialogue Windows

The operational view of extraction buffering. This page answers why a capture
did or did not produce MemoryUnits.

Rows should show session id, dialogue id, status, message count, token count,
seal reason, updated time, and produced unit count. Detail should link back to
the session stream, highlight the covered message range, and list produced
MemoryUnits.

## Memory Units

The primary review workspace. It should use a dense full-width table for
scanning and a routeable detail page for investigation.

Filters:

- owner id;
- namespace list;
- memory type;
- timestamp range;
- redaction state;
- evidence status.

Rows should show timestamp, scope, type, redaction state, short memory text, and
dialogue ref count.

## Dialogue Evidence

This is an audit surface, not a chat UI and not the primary session view. It
shows extraction chunk metadata, selected message ranges, and produced memory
units. Raw message content should be explicitly gated in hosted deployments.

## Operation Logs

Shows capture, read, reindex, export, retention, and redaction operations. Logs
should prefer summaries and ids over raw personal content.

## Retrieval Lab

Simulates runtime recall by calling the real read pipeline. It accepts owner,
namespaces, query, query time, recency policy, max units, and context budget.
It returns ranked units, score breakdowns, and rendered context.

## Index Health

Shows that the index is derived state. Reindex should rebuild from the
authoritative store and be safe to repeat.

## Navigation Model

Keep object links explicit:

```text
query -> ranked MemoryUnit -> DialogueRef -> Dialogue -> OperationLogEntry
```

For manager UX, prefer:

```text
Session message stream -> DialogueWindow overlay -> produced MemoryUnit
MemoryUnit -> DialogueRef -> source Dialogue -> optional highlighted messages
```

Each object should have a stable URL and copyable id. Do not pack every detail
into one page; use links to keep pages readable.
