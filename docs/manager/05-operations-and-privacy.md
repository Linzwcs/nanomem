# Operations And Privacy

Status: active

Admin operations touch private memory data. The default posture should be
local, explicit, auditable, and reversible where possible.

## Boundary Note

As of v0.3.0a5 the heavy maintenance workflows (backup, export, retention,
log retention, integrity, migrations) ship **only** through the `nanomem`
CLI. The HTTP control plane exposes inspection + retrieval-preview +
reindex; everything else is a per-task CLI subcommand. Re-introducing
HTTP endpoints requires a documented control-plane consumer and a UI
design — neither exists today.

## Reindex

The store is authoritative; the index is derived. Reindex
(`POST /manager/api/reindex` or `nanomem reindex`) should:

- select non-redacted memory units from the store;
- rebuild or update the active index;
- report indexed count and backend;
- write an operation log entry of type `reindex`;
- be safe to repeat.

Source dialogue must never be inserted into the retrieval index.

## Backup And Export (CLI)

`nanomem backup` snapshots the SQLite database. `nanomem export` writes a
logical JSON export. Keep export modes separate:

- MemoryUnit-only export;
- MemoryUnit + OperationLog export;
- Raw Dialogue export.

Raw dialogue export should be disabled by default and require operator
permission. Every export should include a manifest with schema version,
counts, timestamp, redaction policy, and checksum.

## Retention (CLI)

Retention uses a preview/apply flow:

```text
nanomem retention-preview      -> affected counts and samples
nanomem retention-apply        -> explicit confirmation + writes log
nanomem log-retention-preview  -> operation log pruning preview
nanomem log-retention-apply    -> applies log pruning
```

Preview returns affected record counts and samples. Apply requires
explicit confirmation and records the operation. If retention removes or
redacts memory units, reindex must run or be clearly marked as required.

## Redaction

Redaction has separate meanings:

- `MemoryUnit.redacted_at`: the fact is no longer eligible for normal
  reads or reindex.
- `Dialogue.redacted_at`: raw source messages are no longer revealable,
  but metadata and refs may remain for audit.
- `OperationLogEntry`: summaries should remain useful while raw payloads
  may be minimized, hashed, or removed.

Do not rely on the UI to hide redacted content. The API and store
selectors must enforce redaction semantics.

A delete/redact CLI subcommand (or HTTP endpoint) is still on the
roadmap; today operators reach into the store directly only via export +
re-import for redaction work.

## Raw Dialogue Reveal

Normal MemoryUnit detail can show source status and metadata. Raw
dialogue content for hosted deployments should eventually move behind a
reveal endpoint:

```text
POST /manager/api/dialogues/{dialogue_id}/reveal
```

Reveal should require permission, reason, and audit logging. Browser logs
must not include raw dialogue content. This endpoint is not yet
implemented.

## Hosted Safety Defaults

- Bind manager/control endpoints to localhost by default.
- Require auth before network exposure.
- Use CSRF protection for state-changing operations.
- Do not expose `/manager` or `/manager/api/*` through MCP or agent
  adapters (MCP is read-only and intentionally cannot reach the manager
  surface).
- Never store provider secrets in browser-readable payloads.
