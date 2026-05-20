# Admin Console Design

Status: draft

This directory defines NanoMem Manager: a human-facing control plane for
observing, auditing, and maintaining long-term personal memory stores.

The admin console is intentionally separate from the core agent-facing APIs.
Agents continue to use `/v1/capture` and `/v1/read`; humans use `/manager` and
the `/admin/api/*` control-plane API to inspect what was stored, why it was
stored, whether retrieval works, and which maintenance operations are needed.

## Reading Order

- `00-control-plane-boundary.md`: what the admin console is and is not.
- `01-information-architecture.md`: page model and object navigation.
- `02-local-mvp.md`: current local implementation and immediate gaps.
- `03-admin-api.md`: endpoint groups, request behavior, and response semantics.
- `04-ui-workflows.md`: UI behavior for memory review, evidence, logs, and retrieval.
- `05-operations-and-privacy.md`: reindex, export, retention, redaction, and raw dialogue safety.
- `06-optimization-roadmap.md`: scaling, UX, and phased implementation.
- `07-behavior-cases.md`: concrete admin acceptance cases.

## Relationship To Core Specs

Core product and runtime memory contracts remain in `docs/nanomem/`:

- `MemoryUnit`, `DialogueRecord`, `DialogueRef`, and `OperationLogEntry`
  semantics belong to `docs/nanomem/02-memory-model.md`.
- `/v1/capture` and `/v1/read` belong to `docs/nanomem/03-capture-api.md` and
  `docs/nanomem/04-read-api.md`.
- extraction, retrieval, ranking, rendering, storage, index backend, and
  adapter decisions belong to the corresponding `docs/nanomem/` specs.

Admin documents explain how humans manage and audit those objects. They should
not introduce a second runtime memory model.
