# Manager Design System

Status: active

NanoMem Manager is a local control plane for inspecting memory state. It should
feel like professional infrastructure software: calm, compact, explicit, and
optimized for repeated debugging work.

## Product Posture

The manager is not a landing page, analytics dashboard, or chat client. It is
a debugging and audit surface for:

```text
Session message stream -> DialogueWindow -> Dialogue chunk -> MemoryUnit -> Retrieval
```

Every screen should answer one of these questions:

- What memory exists?
- Where did it come from?
- Is it searchable?
- Is a session still buffered?
- Which operation changed the store or index?

## Navigation

Primary sections (match `Shell.tsx`):

```text
Overview
Sessions
Dialogue Windows
Memory Units
Retrieval
Operations
Index Health
```

Use stable hash-route URLs for object details. A user should be able to move
from a `MemoryUnit` to its source dialogue (optionally highlighting the
extractor-provided message range), from a `DialogueWindow` to its covered
message range, and from an operation log to affected object ids.

## Layout Rules

Persistent left sidebar (collapsible icon rail on narrow screens) and a
constrained main content surface. Prefer full-width tables and full-width
detail cards over stacked cards or split columns.

Do:

- keep row heights compact and stable;
- collapse filter strips behind a `<details>` element when no filter is set;
- show counts, active filters, and pagination near the table header;
- use detail pages for evidence, metadata, and source logs;
- use monospaced text for ids, JSON, and request payloads;
- drop empty panels (no `{}` Metadata block) rather than render them.

Avoid:

- hero sections, marketing copy, decorative illustrations, nested cards;
- oversized metric tiles on workflow-heavy pages;
- hiding raw ids when they are needed for debugging;
- multi-line table cells when a single-line layout fits;
- full Badges in tight status columns where a colored dot conveys the
  same information.

## Visual Style

Use a Codex-like engineering workbench style: monochrome first, compact, text
driven, and precise. The UI should feel like a local developer tool, not a
colorful admin dashboard.

Roles:

- background: warm near-white;
- surface: white with subtle gray border;
- text: near-black;
- muted text: neutral gray;
- primary accent: black or dark gray for selected navigation and primary
  actions;
- link/info accent: restrained blue only where it improves recognition;
- warning: amber;
- destructive / redaction: red;
- success / synced: low-saturation green, used sparingly (status dot, kept
  row indicator, copied confirmation).

Keep border radius small, spacing even, shadows minimal, typography quiet.
Avoid gradients, glow effects, decorative blobs, and broad color themes.

Use lighter font weights by default. Reserve stronger weights for active
navigation, primary object ids, table emphasis, and primary actions.

## Component Primitives

Familiar controls:

- text inputs for owner, namespace, query filters;
- segmented controls (the time-range preset chips) for canned ranges;
- date pickers for explicit start/end timestamps;
- compact Badges for status, memory type, namespace, backend health;
- icon buttons with tooltips for refresh, copy id, open detail.

Project-specific primitives added during the v0.3 UI overhaul:

### CollapsibleFilters

Wraps any filter input grid inside a `<details>` element. The summary row
shows a caret, the literal word `Filters`, an active-count chip, and any
active filters as dismissable `filter-chip-dismissable` chips with a small
× icon. A `Clear all` ghost-button appears on the right when at least one
filter is set.

Default-collapsed when no filters are set; auto-opens
(`useState(active.length > 0)`) when the URL already has filters. Pair it
with a `placeholderData: keepPreviousData` query so the form does not
unmount mid-keystroke.

### CopyableId

Monospace id chip with truncated middle ellipsis (`unit_b7a3…bcb81b`) and
a one-click copy button that flips the icon to a checkmark for ~1s. Has a
`compact` variant for in-table use (smaller padding + font).

### Score breakdown

For the Retrieval Preview ranked table, the score cell stacks the overall
score (bold) above two muted sub-scores `R` (relevance) and `T` (recency)
pulled from `score_breakdown`. Operators see "did the model rank this
because of similarity or because it's recent?" at a glance.

### Status dot

For tight columns where a full Badge wastes horizontal space, a 9px
colored circle conveys the same status (`status-dot-ok` green,
`status-dot-error` / `status-dot-failed` red, default amber for unknown).
Used in the Operations table.

### Summary overflow indicator

When a row's data has more chips than the column can fit, cap the visible
chips at a small fixed N (Operations uses 3) and append a muted `+N` text
indicator. Eliminates the wobble of a fade-clamp that truncates at random
points.

### Ghost button tiers

- `ghost-button` — white bg, gray border, 30px tall, for secondary form
  actions (Use example, Copy context).
- `ghost-button-compact` — 26px tall with smaller padding + font, for
  rarely-used page-header actions (Rebuild index) that should not compete
  with the page title or status badge.

### Example chips for empty states

Where a form's empty state would otherwise be blank, sample real records
and render them as clickable chips that prefill + submit on click. Used in
Retrieval Preview "Try a query".

## Data Density

Memory management is scan-heavy. Default density should show many rows
without feeling cramped.

Operations rows: ~38px per row — compact time, inline operation type +
oplog id chip, status dot, inline scope, summary chips capped at 3.

Memory Unit rows include: short fact text + CopyableId chip, scope (owner
bold + namespace muted), memory type Badge, source ref count, timestamp.

Dialogue Window rows include: dialogue id chip, session id, status Badge,
message count, token count, produced unit count, updated time.

## Evidence Display

Source evidence should look like an audit log, not a chat app. The default
view is the session's chronological message stream. Show each message with
role, speaker_id, timestamp, and content. Overlay DialogueWindow / chunk
boundaries only as processing metadata. Highlight only the referenced
message range for a selected MemoryUnit.

Do not show produced MemoryUnit counts as if they belong to individual
messages. A MemoryUnit may cite one message, a range, or a chunk; counts
belong at the window, session, or MemoryUnit table level.

Never show hidden reasoning, tool stdout, or external raw artifacts as
ordinary dialogue content. The manager displays only the stored visible
dialogue and metadata.

## Empty And Loading States

Empty states should be factual and actionable:

- no matching memory units;
- no open dialogue windows;
- no operation logs for this filter;
- index is empty but store has active units.

Avoid explanatory product copy. Show the next useful action when obvious,
such as clearing filters, running reindex, or clicking an example chip.

Empty detail panels (empty Metadata block, no produced units) drop the
section rather than render an empty card.

## Design QA Checklist

Before shipping manager UI changes:

- verify desktop and narrow viewport layouts;
- confirm tables do not overflow horizontally except in intentional data
  grids;
- confirm long ids, namespaces, memory text wrap or truncate predictably;
- type into every filter input — focus must stay on the input across
  refetches (regression for the `keepPreviousData` fix);
- click every chip in `Try a query` and confirm prefill + auto-run;
- verify filter strip auto-opens when deep-linked with active filters;
- verify Cmd/Ctrl+Enter submits the Retrieval Preview form;
- verify Copy on the Rendered Context block;
- test empty, loading, error, and stale-index states;
- run the browser manager against a multi-session fixture database.
