# Behavior Cases

Status: active

These cases define expected manager behavior. Core memory behavior is
covered by `docs/nanomem/11-behavior-cases.md`. Workflows that ship only
through the CLI today (backup / export / retention / redaction) are not
included in this manager-facing list.

## Memory List

Given an owner with many namespaces, the operator filters by `owner_id`,
`namespace`, memory type, and time range. The list returns paginated
`MemoryUnit` rows and does not include redacted units unless an
`include_redacted=true` selector is allowed by the store query.

## Filter Strip Behavior

Given the operator opens `/memory-units` with no query string, the
collapsible filter strip is closed. Given the operator opens
`/memory-units?owner_id=alice`, the strip auto-opens, the `Owner: alice`
chip appears in the summary, and a `Clear all` button is shown.

## Filter Input Focus

Given the operator types into any filter input, the input keeps focus
across the resulting refetch (regression for the `keepPreviousData` fix).
The list shows previous data with a loading indicator rather than
unmounting and remounting the form.

## Session Stream

Given a session with multiple dialogue windows, the session detail page
shows the chronological message stream first and overlays DialogueWindow
boundaries on top of it. Open windows badge as `open`; sealed windows
badge as `extracted` or `failed`.

## Dialogue Window Status

Given a dialogue window has not yet been extracted, the
`/dialogue-windows` list shows it with `open` status and zero produced
units. After extraction, status flips to `extracted` and the produced
unit count populates.

## Memory Evidence

Given a MemoryUnit with a valid `DialogueRef`, the detail page resolves
the referenced `Dialogue`, applies the half-open message range, and
displays source status `ok`.

If the dialogue is missing, status is `missing_dialogue`. If the dialogue
is redacted, status is `redacted_dialogue` and raw message content is
not returned. If the range is empty or clamped, the UI shows that exact
status.

## Memory Detail Lifecycle Fields

Given a MemoryUnit has no `retention_until` and no `redacted_at`, the
fact card's meta grid shows Owner / Namespace / Available at / Source.
Given either lifecycle field is set, the matching column appears; the
optional fields do not render an empty placeholder.

Given a MemoryUnit's metadata is `{}`, the Metadata panel does not render
at all (rather than rendering an empty JSON block).

## Retrieval Preview First Run

Given the operator opens `/retrieval-preview` for the first time, the
"Try a query" panel shows up to three example chips sampled from real
stored units (one per distinct owner+namespace). Clicking a chip prefills
Owner / Namespaces / Query and submits without an extra click.

## Retrieval Preview Submit

Given owner `user-sim`, namespace `personal`, and query
`concise Chinese answers`, Retrieval Preview calls the real read pipeline
and shows ranked memory units with overall score + R/T sub-scores +
token estimates. Kept rows show a green left bar; cut rows render dimmed
with a `cut` pill in the tokens cell.

Given the operator presses Cmd/Ctrl+Enter inside the Query textarea, the
form submits the same way as clicking Run preview.

## Retrieval Context Copy

Given results are visible, clicking the Copy button on the Rendered
Context panel writes the full rendered text to the clipboard and flips
the icon to a checkmark for ~1s.

## Operations Status Dot

Given an operation log row, the Status column shows a 9px colored dot:
green for `ok`, red for `error` / `failed`, amber for unknown. The dot
is accessible via `aria-label` set to the status string.

## Operations Summary Overflow

Given an operation log entry has more than 3 summary fields, the
Operations row shows the first 3 as chips plus a muted `+N` indicator
for the remainder. Individual chips truncate at 200px so a long
`dialogue_id` value does not push other chips out.

## Index Lag

Given store unit count is greater than index document count, Index Health
shows lag in the Delta card. Running Rebuild rebuilds the active index
from the authoritative store, reports indexed count, and records the
operation.

## Permission Boundary

The single local-operator role can perform every action exposed by the
HTTP control plane today (inspection + retrieval preview + reindex). The
heavier privacy / maintenance workflows are CLI-only and inherit local
filesystem permissions. Role separation for hosted deployments is a
future phase (see `06-optimization-roadmap.md`).
