# Manager Design

Status: active

This directory defines NanoMem Manager: a human-facing control plane for
observing, auditing, and maintaining long-term personal memory stores.

The manager is intentionally separate from the core agent-facing APIs.
Agents continue to use `/v1/capture` and `/v1/read`; humans use `/manager`
and the `/manager/api/*` control-plane API to inspect what was stored,
why it was stored, whether retrieval works, and which maintenance
operations are needed.

The browser app is React 19 + Vite 8, built from `manager-ui/` into
`src/nanomem/admin/manager_ui/`. The Python HTTP server serves the
compiled assets from package resources. No second web server, no
client-side router beyond hash routes.

## Reading Order

- `00-control-plane-boundary.md`: what the manager is and is not.
- `01-information-architecture.md`: page model and object navigation.
- `02-local-mvp.md`: current local implementation and immediate gaps.
- `03-control-api.md`: endpoint inventory, request behavior, and
  out-of-scope (CLI-only) workflows.
- `04-ui-workflows.md`: UI behavior for memory review, evidence, logs,
  retrieval preview, and the filter strip / scoring / button patterns.
- `05-operations-and-privacy.md`: reindex, the CLI-only
  backup/export/retention workflows, redaction semantics, raw dialogue
  safety.
- `06-optimization-roadmap.md`: scaling, UX, and phased implementation
  status.
- `07-behavior-cases.md`: concrete manager acceptance cases.
- `08-react-frontend-architecture.md`: React/Vite source tree, runtime
  stack, frontend boundaries.
- `09-design-system.md`: visual system, component primitives, interaction
  standards, design QA.

## Relationship To Core Specs

Core product and runtime memory contracts remain in `docs/nanomem/`:

- `MemoryUnit`, `Dialogue`, `DialogueRef`, and `OperationLogEntry`
  semantics belong to `docs/nanomem/02-memory-model.md`.
- `/v1/capture` and `/v1/read` belong to `docs/nanomem/03-capture-api.md`
  and `docs/nanomem/04-read-api.md`.
- extraction, retrieval, ranking, rendering, storage, index backend, and
  adapter decisions belong to the corresponding `docs/nanomem/` specs.
- `docs/nanomem/15-web-management-console.md` keeps a high-level summary
  for cross-reference; concrete UI and control-plane behavior live here.

Manager documents explain how humans manage and audit those objects. They
should not introduce a second runtime memory model.
