# NanoMem Design Specs

Status: draft

This directory contains the modular design specification for NanoMem. These
documents describe the intended clean design and may be ahead of the current
implementation.

## Spec Index

- `00-overview.md`: system overview and architecture boundary.
- `01-product-boundary.md`: product scope and non-goals.
- `02-memory-model.md`: conceptual data model and MemoryUnit style.
- `03-capture-api.md`: planned capture API and lifecycle.
- `04-read-api.md`: planned read API, namespace list behavior, and result shape.
- `05-extraction.md`: extraction rules, chunking, speaker handling, and quality gates.
- `06-retrieval-ranking-render.md`: candidate retrieval, ranking, and rendering.
- `07-storage.md`: fact store, local data directory, migrations, and retention.
- `08-index-backends.md`: in-memory, LanceDB, and Postgres/pgvector strategy.
- `09-configuration.md`: configuration schema and defaults.
- `10-interfaces-and-integration.md`: core interfaces and adapter integration.
- `11-behavior-cases.md`: expected behavior in concrete product scenarios.
- `12-operations-privacy.md`: operations, privacy, export, and delete.
- `13-roadmap.md`: staged implementation plan.
- `14-contract-freeze-review.md`: field-by-field review before v1 contract freeze.
- `15-web-management-console.md`: high-level control-plane web console boundary.

## Related Manager Specs

Detailed manager design, API planning, UI workflows, operations, privacy, and
rollout notes live in `../manager/`. Keep durable memory contracts in this
directory, and put human-facing management-platform details in `docs/manager/`.
