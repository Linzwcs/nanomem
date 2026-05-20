# Operations And Privacy

Status: draft

Admin operations touch private memory data. The default posture should be local,
explicit, auditable, and reversible where possible.

## Reindex

The store is authoritative; the index is derived. Reindex should:

- select non-redacted memory units from the store;
- rebuild or update the active index;
- report indexed count and backend;
- write an operation log;
- be safe to repeat.

Source dialogue must never be inserted into the retrieval index.

## Backup And Export

Backups preserve operational recoverability. Exports support portability and
inspection. Keep the modes separate:

- MemoryUnit-only export.
- MemoryUnit + OperationLog export.
- Raw DialogueRecord export.

Raw dialogue export should be disabled by default and require admin permission.
Every export should include a manifest with schema version, counts, timestamp,
redaction policy, and checksum.

## Retention

Retention should use a preview/apply flow.

Preview returns affected record counts and samples. Apply requires explicit
confirmation and records the operation. If retention removes or redacts memory
units, reindex must run or be clearly marked as required.

## Redaction

Redaction has separate meanings:

- `MemoryUnit.redacted_at`: the fact is no longer eligible for normal reads or
  reindex.
- `DialogueRecord.redacted_at`: raw source messages are no longer revealable,
  but metadata and refs may remain for audit.
- `OperationLogEntry`: summaries should remain useful while raw payloads may be
  minimized, hashed, or removed.

Do not rely on the UI to hide redacted content. The API and store selectors
must enforce redaction semantics.

## Raw Dialogue Reveal

Normal MemoryUnit detail can show source status and metadata. Raw dialogue
content should eventually move behind a reveal endpoint:

```text
POST /admin/api/dialogues/{dialogue_id}/reveal
```

Reveal should require permission, reason, and audit logging. Browser logs must
not include raw dialogue content.

## Hosted Safety Defaults

- Bind admin to localhost by default.
- Require auth before network exposure.
- Use CSRF protection for state-changing operations.
- Do not expose admin endpoints through MCP or agent adapters.
- Never store provider secrets in browser-readable payloads.
