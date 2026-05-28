# UI Workflows

Status: active

The manager UI should make memory state explainable without turning dialogue
into the main product surface.

## Filter Strip Pattern

Every list page (Memory Units, Operations, Dialogue Windows, Sessions) wraps
its filter inputs in `CollapsibleFilters`:

- The strip is one slim row by default. Summary shows a caret, the literal
  word `Filters`, an active-count chip, and any active filters as
  dismissable chips (`Owner: alice ×`). When no filters are set, the
  summary shows a hint (`All active memory units`).
- Strip auto-opens when the URL already has active filters
  (`useState(active.length > 0)`); otherwise stays closed.
- Clicking a chip's × removes that filter; "Clear all" appears on the right
  when at least one filter is set.
- All list-page queries set `placeholderData: keepPreviousData` so the strip
  does not unmount mid-keystroke and inputs keep their focus while a
  refetch is in flight.

## Memory Review

Default to the `Memory Units` list. Operators should scan recent facts,
filter by owner, namespace, type, time range, and order, then open a
full-page detail route.

Time filtering uses `TimeRangeFilter`: quick presets (`All`, `Last 7 days`,
`Last 30 days`, `Last 90 days`, `This month`) plus explicit start and end
dates. Visible dates are local calendar dates; requests must send concrete
ISO boundaries so a selected end date includes the whole day.

The detail page uses this structure:

```text
Status chip strip + timestamp
Fact card (text + meta grid with Owner / Namespace / Available at / Source)
Source Dialogue (status + range + messages, with raw-reveal gating)
Metadata (only when non-empty)
```

The fact card spans full width. Unit id is shown as a `CopyableId` chip in
the card header. Optional lifecycle fields (Retention until, Redacted at)
only render when the underlying value is non-null.

## Evidence Display

Source dialogue is evidence, not a chat replay.

Default display per source chunk:

- source status badge (`ok` / `missing_dialogue` / `redacted_dialogue` /
  `empty_range` / `out_of_range_clamped`);
- session id (link) and dialogue id (mono chip);
- exact `range_label` (`Full dialogue` or extractor-provided range);
- extracted messages in a compact transcript with role / speaker / time.

For hosted deployments, raw message content should require explicit reveal
and write an audit log. Missing / redacted / empty / clamped ranges have
distinct status badges so operators can distinguish data loss from policy
hiding.

## Retrieval Preview

Runtime recall simulator, not a general search box. The form bisects into:

- A compact primary row: Owner / Namespaces / Use example / Run preview.
- A wide Query textarea — Cmd/Ctrl+Enter inside the textarea submits.
- A `Tuning` `<details>` disclosure that collapses Budget tokens /
  Max units / Query time / TimeRange behind a summary chip showing the
  current settings.

Empty state (no preview run yet) shows a "Try a query" panel with up to
three example chips sampled from real stored MemoryUnits (one per distinct
owner+namespace). Clicking a chip prefills the form and submits.

Results:

- 4 metric cards: candidate / ranked / rendered / skipped.
- Ranked table:
  - **Rank** with a green left-bar on kept rows;
  - **Memory** — fact text + timestamp + namespace inline; click opens
    the unit detail page;
  - **Score** — bold overall score on the first line, R (relevance) and
    T (recency) sub-scores from `score_breakdown` on the second line;
  - **Tokens** — estimate from `ranked_token_estimates`, with a small
    `cut` pill when the unit did not make the rendered context.
  - Cut rows are dimmed so kept vs. cut is fast to scan.
- Rendered Context panel — budget badge + Copy button + the rendered
  text. Copy uses `navigator.clipboard.writeText` and flips the icon to
  a checkmark for ~1s.

Retrieval Preview has two distinct time controls in Tuning:

- `query_time`: the simulated current time for recency ranking;
- memory `time range`: a hard filter over MemoryUnit evidence timestamps.

These remain visually separate because changing `query_time` changes
ranking, while changing the memory range changes which facts are eligible
for retrieval at all.

## Operation Logs

The Operations table is optimized for high scan density:

- Compact `MM/DD/YY HH:mm` time format (`formatTimeShort`); the cell never
  wraps to a second line.
- Operation type + copyable oplog id chip inline on one row
  (`white-space: nowrap` on the type keeps words like "capture" intact).
- Status as a 9px colored dot (green for `ok`, red for `error` / `failed`,
  amber for unknown) — replaces the per-row Badge that wasted a column.
- Scope inline as `owner · namespace` (namespace omitted when `default`).
- Summary chips capped at 3 per row with a muted `+N` overflow indicator;
  individual chips truncate at `max-width: 200px` so a long `dialogue_id`
  does not push other chips out.

Filters: operation type, status, owner, namespace, time range, row limit.

The operation-log time range applies to log creation time, not the
underlying memory evidence time. A log detail view (future) should show
summary first and raw payload only when useful.

## Index Health

4 hero metric cards: Active units / Index documents / Delta / Backend.
Backend details panel surfaces fields not already in the cards
(embedding model, dense scan limit, etc.) and renders nothing when
those extras are empty.

The Rebuild index action uses `ghost-button-compact` (≈26px tall, matching
the `synced` badge) — it is rarely needed on a healthy index, so the visual
weight stays low.

## Button Hierarchy

- Default `button` (solid dark) — form submit actions where the action is
  the obvious next step (Run preview).
- `ghost-button` — secondary actions inside form action rows (Use example).
- `ghost-button-compact` — operator-only actions in page headers
  (Rebuild index) that should not compete with page titles.

Form-row buttons (`.retrieval-actions button`) are pinned to 34px so they
line up with the input fields next to them.

## Empty And Error States

Every page should have explicit states for:

- no matching records;
- missing dialogue reference;
- redacted dialogue;
- stale or empty index;
- permission denied (future);
- failed control operation.

These are part of the product because operators need to distinguish normal
absence from data integrity problems. Empty detail panels are dropped
entirely (no `{}` Metadata block) rather than rendered as empty cards.
