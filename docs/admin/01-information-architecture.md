# Information Architecture

Status: draft

The admin console should be organized around stable NanoMem objects and the
links between them.

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

## Overview

Shows store and index health:

- store backend, path, schema version, migration status;
- memory unit, owner, namespace, dialogue, and operation log counts;
- active index backend and indexed document count;
- index lag: `store unit_count - index_document_count`;
- oldest and newest memory timestamps;
- top owner/namespace pairs.

## Memory Units

The primary review workspace. It should use a dense full-width table for
scanning and a routeable detail page for investigation.

Filters:

- owner id;
- namespace list;
- memory type;
- timestamp range;
- confidence bucket;
- redaction state;
- evidence status.

Rows should show timestamp, scope, type, confidence, redaction state, short
memory text, and dialogue ref count.

## Dialogue Evidence

This is an audit surface, not a chat UI. It shows source dialogue metadata,
selected message ranges, and produced memory units. Raw message content should
be explicitly gated in hosted deployments.

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
query -> ranked MemoryUnit -> DialogueRef -> DialogueRecord -> OperationLogEntry
```

Each object should have a stable URL and copyable id. Do not pack every detail
into one page; use links to keep pages readable.
