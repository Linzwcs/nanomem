# Manager Design

Status: draft

This directory defines NanoMem Manager: a human-facing control plane for
observing, auditing, and maintaining long-term personal memory stores.

The manager is intentionally separate from the core agent-facing APIs.
Agents continue to use `/v1/capture` and `/v1/read`; humans use `/manager` and
the `/manager/api/*` control-plane API to inspect what was stored, why it was
stored, whether retrieval works, and which maintenance operations are needed.

## Reading Order

- `00-control-plane-boundary.md`: what the manager is and is not.
- `01-information-architecture.md`: page model and object navigation.
- `02-local-mvp.md`: current local implementation and immediate gaps.
- `03-control-api.md`: endpoint groups, request behavior, and response semantics.
- `04-ui-workflows.md`: UI behavior for memory review, evidence, logs, and retrieval.
- `05-operations-and-privacy.md`: reindex, export, retention, redaction, and raw dialogue safety.
- `06-optimization-roadmap.md`: scaling, UX, and phased implementation.
- `07-behavior-cases.md`: concrete manager acceptance cases.
- `08-react-frontend-architecture.md`: proposed React/Vite frontend boundary.
- `09-design-system.md`: visual system, interaction standards, and design QA.

## Relationship To Core Specs

Core product and runtime memory contracts remain in `docs/nanomem/`:

- `MemoryUnit`, `Dialogue`, `DialogueRef`, and `OperationLogEntry`
  semantics belong to `docs/nanomem/02-memory-model.md`.
- `/v1/capture` and `/v1/read` belong to `docs/nanomem/03-capture-api.md` and
  `docs/nanomem/04-read-api.md`.
- extraction, retrieval, ranking, rendering, storage, index backend, and
  adapter decisions belong to the corresponding `docs/nanomem/` specs.

Manager documents explain how humans manage and audit those objects. They should
not introduce a second runtime memory model.
