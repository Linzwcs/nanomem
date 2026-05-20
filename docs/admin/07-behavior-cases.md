# Behavior Cases

Status: draft

These cases define expected admin-console behavior. Core memory behavior remains
covered by `docs/nanomem/11-behavior-cases.md`.

## Memory List

Given an owner with many namespaces, the operator filters by `owner_id`,
`namespace`, memory type, and time range. The list returns paginated
`MemoryUnit` rows and does not include redacted units unless
`include_redacted=true` is allowed.

## Memory Evidence

Given a MemoryUnit with a valid `DialogueRef`, the detail page resolves the
referenced `DialogueRecord`, applies the half-open message range, and displays
source status `ok`.

If the dialogue is missing, status is `missing_dialogue`. If the dialogue is
redacted, status is `redacted_dialogue` and raw message content is not returned.
If the range is empty or clamped, the UI shows that exact status.

## Retrieval Preview

Given owner `user-sim`, namespace `personal`, and query
`concise Chinese answers`, Retrieval Lab calls the real read pipeline and shows
ranked memory units, scores, and rendered context. Results link back to source
evidence.

## Index Lag

Given store unit count is greater than index document count, Index Health shows
lag. Running reindex rebuilds from the authoritative store, reports indexed
count, and records the operation.

## Retention Preview

Given a retention selector, preview returns affected MemoryUnits,
DialogueRecords, and OperationLogs with counts and samples. No data changes
until apply is confirmed.

## Redaction

Given a MemoryUnit is redacted, normal reads and reindex exclude it. Admin users
with permission may view metadata and redaction state. Strong redaction may
replace text according to policy.

## Raw Dialogue Reveal

Given a hosted deployment, raw source dialogue is not shown by default. A reveal
operation requires permission and reason, then writes an audit log.

## Export

Given an export request, MemoryUnit-only export excludes raw dialogue. Raw
DialogueRecord export requires explicit admin mode and writes a manifest with
schema version, counts, checksum, and timestamp.

## Permission Failure

Given a Viewer attempts reindex, export, redact, delete, or raw reveal, the API
returns permission denied and the UI explains which role is required.
