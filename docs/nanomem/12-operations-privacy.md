# Operations And Privacy

Status: draft

This document defines NanoMem's control-plane operations and privacy boundary.

## 1. Purpose

Operations manage stored personal data. They are separate from agent-facing
`capture` and `read`.

Agent-facing tools should not expose backup, export, retention, delete,
redaction, reindex, integrity checks, or raw DialogueRecord inspection.

## 2. Control-Plane Operations

Recommended operations:

- `backup`: create a physical operational backup;
- `export`: produce logical user-data exports;
- `retention_preview`: show records that would expire;
- `retention_apply`: apply retention policy;
- `delete` / `redact`: remove or redact user data;
- `reindex`: rebuild derived indexes from the authoritative store;
- `integrity_check`: verify schema, refs, and index consistency;
- `inspect_dialogue`: read DialogueRecords for audit or debugging.

These operations may require stronger authorization than normal memory tools.

## 3. Data Classes

NanoMem stores three privacy-relevant classes:

- `MemoryUnit`: durable personal facts used by read;
- `DialogueRecord`: raw user-visible dialogue evidence, control-plane only;
- `OperationLogEntry`: operational traces and summaries.

They need separate retention policies because they have different risk and
utility profiles.

## 4. Retention

Retention should be explicit and previewable.

Rules:

- MemoryUnit retention removes facts from read and updates indexes.
- DialogueRecord retention removes audit evidence but should not silently change
  MemoryUnit text.
- Operation log retention removes operational traces only.
- Retention apply should be idempotent and recorded in an operation log.

## 5. Delete And Redaction

Delete/redaction should:

- operate from authoritative store records;
- update or rebuild derived indexes;
- avoid preserving sensitive raw text in operation logs;
- keep enough non-sensitive audit state to explain that an operation occurred;
- never be exposed as an ordinary agent-facing memory tool.

If a DialogueRecord is redacted, MemoryUnits that rely on it may remain only if
policy allows facts without inspectable raw dialogue evidence.

## 6. Export

Exports should be explicit about included data.

Default user export should include:

- MemoryUnits;
- timestamps;
- owner and namespace;
- metadata selected by policy;
- dialogue refs as ids and ranges.

DialogueRecords should require an explicit raw-dialogue export mode because
they contain user-visible dialogue content.

## 7. Security Defaults

Defaults should favor local privacy:

- use local SQLite by default;
- keep generated files under `data_dir`;
- reference secrets through environment variables;
- avoid sending raw DialogueRecords to agent-facing tools;
- avoid storing raw external resources;
- log summaries instead of raw personal content where possible.
