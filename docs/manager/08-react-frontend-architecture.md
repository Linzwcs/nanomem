# React Frontend Architecture

Status: active

NanoMem Manager is a static React 19 + Vite 8 application. The source tree
lives in `manager-ui/`; the build emits into `src/nanomem/admin/manager_ui/`
so the Python HTTP server keeps serving `/manager` and `/manager/assets/*`
from package resources. NanoMem does not add a second web server or a
Next.js runtime for the local manager.

## Source Tree

```text
manager-ui/
  package.json
  vite.config.ts
  tsconfig.json
  src/
    api/
      client.ts          fetch wrappers for /manager/api/*
      types.ts           response shapes (MemoryUnit, SessionSummary, ...)
    app/
      App.tsx            top-level route switch
      routes.ts          useHashRoute hook + Route union
    components/
      Shell.tsx          left sidebar + main surface
      CollapsibleFilters.tsx   <details> filter strip + active-chip summary
      CopyableId.tsx     truncated id chip with one-click copy
      TimeRangeFilter.tsx      preset chips + start/end date inputs
      Status.tsx         Badge / EmptyState / ErrorState / LoadingState
    features/
      overview/                OverviewPage
      sessions/                SessionsPage + SessionDetailPage
      dialogue-windows/        DialogueWindowsPage
      memory-units/            MemoryUnitsPage + MemoryUnitDetailPage
      retrieval-preview/       RetrievalPreviewPage
      operations/              OperationsPage
      index-health/            IndexHealthPage
    lib/
      format.ts          formatTime / formatTimeShort / truncateId / ...
      timeFilters.ts     local-date <-> ISO boundary helpers
    styles/
      global.css         single-file CSS (no per-component modules)
```

`npm run build` runs `tsc` then `vite build` and writes
`index.html` + `app.js` + `styles.css` into
`../src/nanomem/admin/manager_ui/`. The Python package then ships those
assets via its `package-data` declaration.

## Runtime Stack

- React 19 + TypeScript 5.
- TanStack Query for `/manager/api/*` server state, refresh, and error
  handling. All list-page queries set
  `placeholderData: keepPreviousData` so filter inputs do not unmount
  while a refetch is in flight (fix for the focus-loss bug).
- TanStack Table for the MemoryUnit table; other tables render inline
  with hand-written rows when the column logic is simple.
- lucide-react for icons.
- Hash routes (`useHashRoute` in `app/routes.ts`). No History API, no
  React Router.

Test tooling: Vitest + Testing Library for component tests; Playwright is used
for browser smoke flows in `/tmp/pw-driver/` style ad hoc scripts during
development.

## Frontend Boundaries

`api/` owns HTTP calls and response normalization. Components never build URLs
by hand and never construct `URLSearchParams` for the `/manager/api/*`
surface — that belongs in `api/client.ts`.

`features/` owns per-route domain workflows:

- `overview`: hero metric + sub-metrics + storage / top-namespaces panels.
- `sessions`: capture-stream list + detail (message stream, windows,
  produced units).
- `dialogue-windows`: extraction lifecycle table.
- `memory-units`: filtered review list + detail page (fact card +
  lifecycle + source dialogue).
- `retrieval-preview`: query form + Tuning disclosure + ranked table with
  R/T score breakdown + rendered context with Copy button.
- `operations`: audit log with single-line rows, status dot, summary `+N`
  overflow.
- `index-health`: hero metrics + backend details + compact Rebuild action.

`components/` owns reusable UI primitives. New components added in the recent
UI overhaul:

- `CollapsibleFilters` — wraps a `<details>` element around any filter input
  grid. Summary row shows dismissable active-filter chips and a Clear all
  button when filters are set. Auto-opens (via `useState(active.length > 0)`)
  when the URL already has filters; otherwise stays closed.
- `CopyableId` — monospace id chip with truncated middle ellipsis and a
  one-click copy button. Has a `compact` variant for table cells.

## Visual Direction

Manager is a control plane, not a landing page. The shipping conventions:

- Full-width app shell, left sidebar (collapsible), constrained main surface.
- Table-first review pages with stable, dense rows.
- Filter strips collapse by default; expand when a filter is set.
- Detail pages prefer full-width cards over split column layouts.
- Status dots beat full Badges in tight columns (Operations status).
- Primary buttons are dark; secondary actions use `ghost-button`; rare
  high-cost actions like Rebuild index use `ghost-button-compact` so they
  do not compete with page titles.
- URL-backed filter state on every list page.

## Migration Notes

The package path moved across two refactors:

1. `nanomem.manager.assets` → `nanomem.ops.manager_assets` (v0.3.0a1).
2. `nanomem.ops.manager_assets` → `nanomem.admin.manager_ui` (v0.3.0a5).

`vite.config.ts` writes to the current path; the Python server reads it via
`importlib.resources` against the `_MANAGER_ASSET_PACKAGE` constant in
`transports/http/manager.py`.

The Control API stays stable across UI changes — UI work never introduces
new memory contracts. New API endpoints land in `03-control-api.md` first.
