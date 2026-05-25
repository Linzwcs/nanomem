# Manager Design System

Status: draft

NanoMem Manager is a local control plane for inspecting memory state. Its design
should feel like professional infrastructure software: calm, compact, explicit,
and optimized for repeated debugging work.

## Design Sources

Use public UI/admin-dashboard skills as references, not as installed runtime
dependencies. Third-party `SKILL.md` files can shape agent behavior, so NanoMem
keeps its own project-specific rules here.

Useful source patterns:

- admin dashboard information architecture: tables, filters, detail pages,
  maintenance actions, and audit logs;
- shadcn-style component discipline: consistent inputs, badges, tabs, menus,
  dialogs, and data tables;
- UI design skills: start from workflow and visual direction before coding,
  then validate responsive behavior and accessibility.

## Product Posture

The manager is not a landing page, analytics dashboard, or chat client. It is a
debugging and audit surface for:

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

Primary sections:

```text
Overview
Sessions
Dialogue Windows
Memory Units
Retrieval
Operations
Index Health
```

Use stable URLs for object details. A user should be able to move from a
`MemoryUnit` to its source dialogue, optionally highlight the extractor-provided
message range inside that dialogue, move from a `DialogueWindow` to its covered
message range, and move from an operation log to affected object ids.

## Layout Rules

Use a persistent left sidebar and a constrained main content surface. Prefer
full-width tables and split detail layouts over stacked cards.

Do:

- keep row heights compact and stable;
- put filters in a single toolbar above tables;
- show counts, active filters, and pagination near the table header;
- use detail pages for evidence, metadata, and source logs;
- use monospaced text for ids, JSON, and request payloads.

Avoid:

- hero sections, marketing copy, decorative illustrations, and nested cards;
- oversized metric tiles on workflow-heavy pages;
- long scroll-only pages when tabs or detail sections are clearer;
- hiding raw ids when they are needed for debugging.

## Visual Style

Use a Codex-like engineering workbench style: monochrome first, compact, text
driven, and precise. The UI should feel like a local developer tool, not a
colorful admin dashboard.

Recommended roles:

- background: warm near-white;
- surface: white with subtle gray border;
- text: near-black;
- muted text: neutral gray;
- primary accent: black or dark gray for selected navigation and primary actions;
- link/info accent: restrained blue only where it improves recognition;
- warning: amber;
- destructive/redaction: red;
- success/synced: low-saturation green, used sparingly.

Keep border radius small, spacing even, shadows minimal, and typography quiet.
Avoid gradients, glow effects, decorative blobs, and broad color themes.

Use lighter font weights by default. Reserve stronger weights for active
navigation, primary object ids, table emphasis, and primary actions. Navigation
should support a controllable collapsed icon rail on desktop, with labels still
available through titles/tooltips and full labels restored on narrow screens.

## Components

Use familiar controls:

- text inputs for owner, namespace, and query filters;
- segmented controls or tabs for lifecycle states;
- date range picker for timestamp filtering;
- compact badges for status, memory type, namespace, and backend health;
- icon buttons with tooltips for refresh, copy id, open detail, and rebuild;
- confirmation dialogs for destructive or expensive operations.

Buttons should use icons when the action is common. Text buttons are acceptable
for clear commands such as `Rebuild index` or `Run retrieval`.

## Data Density

Memory management is scan-heavy. Default density should show many rows without
feeling cramped.

Memory Unit rows should include:

- timestamp;
- owner and namespace;
- memory type;
- short memory text;
- evidence count;
- status.

Dialogue Window rows should include:

- session id;
- dialogue id;
- status;
- message count;
- token count;
- seal reason;
- updated time.

## Evidence Display

Source evidence should look like an audit log, not a chat app. The default view
is the session's chronological message stream. Show each message with role,
speaker id, timestamp, and content. Overlay DialogueWindow/chunk boundaries only
as processing metadata. Highlight only the referenced message range for a
selected MemoryUnit.

Do not show produced MemoryUnit counts as if they belong to individual
messages. A MemoryUnit may cite one message, a range of messages, or a chunk;
counts belong at the window, session, or MemoryUnit table level.

Never show hidden reasoning, tool stdout, or external raw artifacts as ordinary
dialogue content. The manager should display only the stored visible dialogue
and metadata.

## Empty And Loading States

Empty states should be factual and actionable:

- no matching memory units;
- no open dialogue windows;
- no operation logs for this filter;
- index is empty but store has active units.

Avoid explanatory product copy. Show the next useful action when obvious, such
as clearing filters or running reindex.

## Design QA Checklist

Before shipping manager UI changes:

- verify desktop and narrow viewport layouts;
- check tables do not overflow horizontally except in intentional data grids;
- confirm long ids, namespaces, and memory text wrap or truncate predictably;
- verify filters persist when opening and returning from detail pages;
- test empty, loading, error, and stale-index states;
- inspect source dialogue highlighting for single-message and multi-message refs;
- run the browser manager against a multi-session fixture database.
