# React Frontend Architecture

Status: active draft

NanoMem Manager has outgrown the build-free single-file UI. The current app is
useful as a local MVP, but memory review, evidence inspection, retrieval
diagnostics, and maintenance workflows need explicit frontend boundaries.

## Technology Choice

Use a static React application built by Vite. The source tree is:

```text
manager-ui/
  package.json
  vite.config.ts
  src/
    api/
    app/
    components/
    features/
      memory-units/
      dialogues/
      retrieval-preview/
      operations/
      index-health/
    styles/
```

Build output should be copied into `src/nanomem/manager/assets/` so the Python
HTTP server keeps serving `/manager` and `/manager/assets/*`. NanoMem should not
add a second web server or a Next.js runtime for the local manager.

Recommended libraries:

- React + TypeScript for component structure and typed UI state.
- TanStack Query for `/manager/api/*` server state, refresh, and error handling.
- TanStack Table for sortable, filterable MemoryUnit and operation-log tables.
- lucide-react for compact icon buttons.
- Vitest and Testing Library for component tests.
- Playwright for browser smoke tests once workflows stabilize.

## Frontend Boundaries

`api/` owns HTTP calls and response normalization. Components should not build
URLs by hand.

`features/` owns domain workflows:

- `memory-units`: list, filters, review queues, detail route, evidence status.
- `dialogues`: log-style source display and produced-unit navigation.
- `retrieval-preview`: query form, ranked hits, ranked/rendered comparison,
  skipped-due-to-budget diagnostics, and rendered context.
- `operations`: operation logs, backup/export, retention and redaction previews.
- `index-health`: backend name, active store count, index document count,
  synced/stale state, last reindex timestamp, and rebuild action result.

`components/` owns reusable UI primitives: page shell, toolbar, table, empty
state, badges, time range controls, JSON preview, and confirm dialogs.

## Visual Direction

Manager is a control plane, not a landing page. Favor dense, quiet layouts:

- full-width app shell with left navigation and top filter bar;
- table-first MemoryUnit review with stable row heights;
- detail pages that show fact, metadata, and source dialogue as log entries;
- badges for namespace, memory type, confidence, evidence, and lifecycle state;
- URL-backed date range, namespace, type, owner, confidence, and text filters;
- paginated lists that preserve filter state when navigating to detail pages;
- no decorative hero sections, nested cards, or dashboard-heavy graphics.

## Migration Plan

1. Keep `manager-ui/` as the editable source of the management console.
2. Build directly into `src/nanomem/manager/assets/` with stable top-level
   `index.html`, `app.js`, and `styles.css` outputs.
3. Keep `src/nanomem/manager/assets/__init__.py` because those files are served
   through Python package resources.
4. Add a Playwright smoke test for `/manager`, memory list, detail source, and
   retrieval preview.

The Control API should remain stable during the frontend rewrite. UI changes
must not introduce new memory contracts.
