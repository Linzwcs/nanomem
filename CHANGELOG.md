# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0a4] — 2026-05-26

Three independently-justified cleanups that strip benchmark-era cruft
and reduce nesting that didn't earn its way. All BREAKING for direct
sub-path imports; top-level `from nanomem import X` unchanged.

### Removed (BREAKING)

- **LLM extractor internal chunking.** The benchmark code's
  `ExtractionChunk`, `message_chunks`, role-segment splitting, and
  per-chunk `max_messages_per_chunk` / `max_chars_per_chunk` knobs are
  gone. The production contract is now: **one Dialogue is one
  extraction unit, sent as one LLM call.** Caller decides dialogue
  boundary via `capture` / `flush` / session window. If a dialogue
  exceeds the model's context, the underlying API error propagates —
  that's a contract violation by the caller, not something to paper
  over with internal splitting.

  Removed from `ExtractionConfig`: `max_messages_per_chunk`,
  `max_chars_per_chunk`. Removed from `ExtractionResult.stats`:
  `chunk_count`, `max_messages_per_chunk`, `max_chars_per_chunk`.
  Removed from `MemoryUnit.metadata`: `chunk_id`, `chunk_message_count`.
  Module `nanomem.pipeline.representation.llm.chunking` deleted.

- **`transports/http/v1/` and `transports/http/manager/`** subpackages
  flattened. Each held one useful file plus an `__init__.py` — paper
  nesting, no navigational value:

  | before | after |
  | --- | --- |
  | `transports.http.v1.schemas` | `transports.http.schemas` |
  | `transports.http.manager.routes` | `transports.http.manager` |
  | `transports.http.manager` (re-export) | `transports.http.manager` |

  Data plane vs control plane is now expressed by file
  (`schemas.py` vs `manager.py`) instead of by directory.

- **`ops/maintenance/` and `ops/tui/`** subpackages flattened to
  `ops/maintenance.py` and `ops/tui.py`. Both were 1-impl-file +
  __init__-re-export shells; the flat file exposes the same names.

- **`ops/manager_assets/`** renamed to **`ops/manager_ui/`** and the
  inner `assets/` subdirectory flattened up one level (the doubled
  name `manager_assets.assets` was awkward). String references
  updated:
  - `_MANAGER_ASSET_PACKAGE` constant in `transports/http/manager.py`
    → `"nanomem.ops.manager_ui"`.
  - `pyproject.toml` `[tool.setuptools.package-data]` key →
    `"nanomem.ops.manager_ui"`.

  | before | after |
  | --- | --- |
  | `ops.maintenance.service.NanoMemMaintenanceService` | `ops.maintenance.NanoMemMaintenanceService` |
  | `ops.tui.dashboard.build_dashboard` | `ops.tui.build_dashboard` |
  | `ops.manager_assets.assets.<file>` | `ops.manager_ui.<file>` |

  `ops/cli/` kept as a package because it ships `__main__.py` for
  `python -m nanomem.ops.cli`.

### Process

160 tests pass (was 163 in v0.3.0a3 — 3 chunking-specific tests
deleted). Layering check green. Three sequential D-batches
(D1: drop chunking, D2: flatten transports/http, D3: flatten ops).

## [0.3.0a3] — 2026-05-26

### Removed (BREAKING)

- **`NanoBotMemoryAdapter`** and **`OpenClawMemoryAdapter`** are gone.
  Both were empty `pass`-style subclasses of `AgentMemoryAdapter` that
  added no behavior — they existed only as naming wrappers. Use
  `AgentMemoryAdapter` directly:

  ```python
  # before
  from nanomem import NanoBotMemoryAdapter, OpenClawMemoryAdapter

  # after
  from nanomem import AgentMemoryAdapter, MemoryScope
  adapter = AgentMemoryAdapter(backend, MemoryScope(owner_id="..."))
  ```

  Top-level exports `NanoBotMemoryAdapter` and `OpenClawMemoryAdapter`
  removed; `nanomem.hosts.adapters.{nanobot,openclaw}` modules deleted.
  The "OpenClaw-like" and "NanoBot-like" prose mentions in docs are
  unchanged — they describe target harness *categories*, not specific
  adapter classes.

## [0.3.0a2] — 2026-05-26

Two paper-aligned production features land on top of the v0.3.0a1
layered architecture. No structural changes; both are pure additions
in their target layers.

### Added

- **`TimeMergedRenderer`** at `nanomem.pipeline.utilization.time_merge`.
  Ports the paper's Time+Merge utilization policy and adds the design
  knob the experimental impl was missing: **the time format string IS
  the merge bucket key**. Coarser format = more facts collapse:

  | `time_format`        | granularity  | typical effect           |
  | -------------------- | ------------ | ------------------------ |
  | `"%Y-%m-%d %H:%M"`   | minute       | near-zero merge          |
  | `"%Y-%m-%d"`         | daily (def.) | typical setting          |
  | `"%Y-%m"`            | monthly      | aggressive merge         |
  | `"%Y"`               | yearly       | extreme merge            |

  Different namespaces stay separate even in the same time bucket.
  Unparseable timestamps land in an explicit `unknown` bucket and
  never merge with parseable ones.

- **`CachedEmbeddingModel`** at `nanomem.pipeline.retrieval.embeddings.cache`.
  Wraps any `EmbeddingModel` with a persistent sqlite-backed cache.
  Key: `(model_name, sha256(text))`. Vectors stored as compact
  `struct.pack` float64 (8 bytes/dim). Drop-in replacement for the
  wrapped model. Essential for affordably running LLM extraction or
  benchmark configs that re-embed the same text repeatedly.

  ```python
  from nanomem import CachedEmbeddingModel, HashingEmbeddingModel

  cached = CachedEmbeddingModel(
      HashingEmbeddingModel(),
      path=".nanomem/embed-cache.db",
  )
  ```

- Both classes are exported at the top level:
  `from nanomem import TimeMergedRenderer, CachedEmbeddingModel,
  EvidenceContextRenderer`.

### Not added (deliberately deferred)

- **`nanomem benchmark` CLI**. Benchmark-grade evaluation belongs in
  the companion `nanomem-exp` repo, not the production CLI. The
  reason is design-substantive, not effort: a benchmark prompt must
  be greedy (eval poses arbitrary questions); a production prompt
  should be selective (users have preferences about what to remember).
  Shipping a single CLI surface for both would mislead users about
  default behavior. For paper-faithful reproduction, see the
  `nanomem-exp` repository.

- **Full read-result cache**. The embedding cache reliably hits on
  repeated `embed()` calls (same text → same vector). A full
  read-result cache would rarely hit (different queries every turn)
  and is hard to invalidate cleanly (any capture potentially
  invalidates every cached result). Embedding cache covers the
  expensive part; read pipeline is fast enough to re-run.

## [0.3.0a1] — 2026-05-26

Paper-aligned horizontal-layering refactor. `src/nanomem/` is now
organized as six layers that match the companion paper's Section 4
figure 1:1. A `tools/check_layering.py` script + `tests/test_layering.py`
machine-enforce the dependency direction.

### Changed (BREAKING)

**Every sub-path import changes.** Top-level `from nanomem import X`
is preserved — all 80+ public symbols remain importable from the top.
The migration table:

| v0.2.x path | v0.3 path |
|-------------|-----------|
| `nanomem.contracts.*` | `nanomem.core.contracts.*` |
| `nanomem.errors` | `nanomem.core.errors` |
| `nanomem.ids` / `nanomem.time` / `nanomem.serde` | `nanomem.core.{ids,time,serde}` |
| `nanomem.policies` | `nanomem.core.policies` |
| `nanomem.config` | `nanomem.core.config` |
| `nanomem.extraction.*` | `nanomem.pipeline.representation.*` |
| `nanomem.store.*` | `nanomem.pipeline.storage.*` |
| `nanomem.index.*` (excl. embeddings) | `nanomem.pipeline.retrieval.indexes.*` |
| `nanomem.index.embeddings.*` | `nanomem.pipeline.retrieval.embeddings.*` |
| `nanomem.ranking.*` | `nanomem.pipeline.retrieval.ranking.*` |
| `nanomem.ranking.ranker` | `nanomem.pipeline.retrieval.ranking.relevance_recency` |
| `nanomem.render.*` | `nanomem.pipeline.utilization.*` |
| `nanomem.render.context` | `nanomem.pipeline.utilization.evidence_context` |
| `nanomem.factory` | `nanomem.service.factory` |
| `nanomem.control.*` | `nanomem.service.control.*` |
| `nanomem.server.*` | `nanomem.transports.http.*` |
| `nanomem.mcp.*` | `nanomem.transports.mcp.*` |
| `nanomem.sdk.*` | `nanomem.transports.sdk.*` |
| `nanomem.maintenance.*` | `nanomem.ops.maintenance.*` |
| `nanomem.cli.*` | `nanomem.ops.cli.*` |
| `nanomem.tui.*` | `nanomem.ops.tui.*` |
| `nanomem.manager.*` | `nanomem.ops.manager_assets.*` |
| `nanomem.adapters.*` | `nanomem.hosts.adapters.*` |
| `nanomem.integrations.*` | `nanomem.hosts.plugins.*` |
| `nanomem.embeddings.*` (deprecation shim) | **removed** — use `nanomem.pipeline.retrieval.embeddings.*` |
| `from nanomem import X` (top-level) | **unchanged** |

Entry-point binaries are unaffected; only the underlying module paths
in `pyproject.toml` changed:
- `nanomem`           → `nanomem.ops.cli.main:main`
- `nanomem-server`    → `nanomem.transports.http.main:main`
- `nanomem-mcp`       → `nanomem.transports.mcp.main:main`
- `nanomem-agent-hook`→ `nanomem.hosts.plugins.hooks:main`

### Added

- `tools/check_layering.py` — AST-walking layering enforcer.
- `tests/test_layering.py` — pytest gate that runs the checker.
- `# layering-exception: <reason>` comment escape hatch for two
  documented composition-root cases (`service/factory.py` constructing
  ops services, `ops/cli/main.py` invoking `install-codex-hooks` from
  hosts).

### Changed (non-breaking)

- File renames within moved layers (semantic honesty):
  - `render/context.py` → `pipeline/utilization/evidence_context.py`
  - `ranking/ranker.py` → `pipeline/retrieval/ranking/relevance_recency.py`
  - `manager/` → `ops/manager_assets/` (the package only bundles
    HTML/CSS/JS; the routes live in `transports/http/manager/`)
  - `integrations/` → `hosts/plugins/` (matches content: agent-harness
    plugins, not generic integrations)
- The 6-layer rule:
  - `core/`       — only stdlib (no other nanomem layers)
  - `pipeline/`   — may import `core`
  - `service/`    — may import `pipeline`, `core`
  - `transports/` — may import `service`, `pipeline`, `core`
  - `ops/`        — may import `service`, `pipeline`, `core`
  - `hosts/`      — may import everything

### Removed

- `nanomem.embeddings` deprecation shim (introduced in v0.2.0a1).
  Use `nanomem.pipeline.retrieval.embeddings` instead.

### Process

Produced as 11 batches (B1–B11) via the `architecture-refactor` skill.
Each batch one commit; pytest green between batches; layering check
green at the end. Inline `# layering-exception` comments are
intentional and reviewed.

## [0.2.0a2] — 2026-05-26

Housekeeping pass on top of the v0.2.0a1 structural refactor. Same
discipline (one batch one commit, tests green between batches,
independent reviewer subagent at the end). No new behavior; only
folder structure, naming, and packaging.

### Changed (BREAKING)

- **`src/nanomem/control/service.py`** is split into
  `control/types.py` (13 result and policy dataclasses) plus
  `control/service.py` (`NanoMemControlService` itself).
  `from nanomem.control import X` and `from nanomem.control.service
  import X` continue to work via the package `__init__` re-export.
  New code may target `from nanomem.control.types import X`.
- **`src/nanomem/extraction/llm.py`** (650 lines) is now a package:
  `extraction/llm/{__init__,extractor,client,chunking,parsing}.py`.
  Every previously-public name (`LLMMemoryUnitExtractor`,
  `LLM_EXTRACTION_PROMPT`, `LLM_EXTRACTION_PROMPT_VERSION`,
  `ALLOWED_MEMORY_TYPES`, `LLMExtractionPayloadError`,
  `ExtractionChunk`, `LLMCompletionClient`,
  `OpenAIChatCompletionClient`, `DEFAULT_MAX_MESSAGES_PER_CHUNK`)
  still imports as `from nanomem.extraction.llm import X`.
- **`src/nanomem/server/`** now mirrors the data-plane vs control-plane
  boundary the docs always described:
  - `server/v1/` — data plane (was `server/schemas.py`)
  - `server/manager/` — control plane (was `server/manager.py`)
  - `server/app.py` and `server/main.py` unchanged in role.
  External imports (`from nanomem.server.manager import
  handle_manager_get`, `from nanomem.server import NanoMemHTTPServer`)
  unchanged.

### Changed (non-breaking)

- **Top-level `nanomem.__init__.py`** is now organized into 8
  commented sections (Contracts / Errors / Service / Capabilities /
  SDK / Adapters / Config & Factory / Admin & Control). Both the
  imports block and `__all__` list share the same ordering.
- **`nanomem_service_with_defaults`** factory helper (added in
  v0.2.0a1) is now exported at the top level —
  `from nanomem import nanomem_service_with_defaults` works.

### Deprecated

- `nanomem.embeddings` shim removal pinned to **v0.3.0** via the new
  `nanomem.embeddings.__deprecated_removal__` constant and an updated
  warning message. Migrate to `nanomem.index.embeddings` before then.

## [0.2.0a1] — 2026-05-26

First structural refactor since the alpha. Goal: tighten interface seams,
align the code layout with the documented architecture, and reserve room
for the implementation work that the companion paper validates (Time+Merge
rendering, LLM extraction with cache, etc.).

### Added

- **`nanomem.errors`** — public exception hierarchy:
  `NanoMemError → {ConfigError, ContractError, StoreError, IndexError_,
  RetrievalError, RenderError, CaptureError → ExtractionError}`. Catch
  `NanoMemError` to catch any library-raised exception.
  `ConfigError`, `ContractError`, `ExtractionError` multi-inherit from
  `ValueError` for backward compatibility.
- **`nanomem.render.base.Renderer`** — Protocol for rendered evidence
  blocks, satisfied by the existing `EvidenceContextRenderer`. Unblocks
  alternative renderers (e.g. the paper's `Time+Merge` policy) without
  service/ changes.
- **`nanomem.ranking.base.Ranker`** — Protocol for ranked memory units,
  satisfied by the existing `MemoryUnitRanker`.
- **`nanomem.extraction.prompts`** — module hosting
  `LLM_EXTRACTION_PROMPT`, `LLM_EXTRACTION_PROMPT_VERSION`, and
  `ALLOWED_MEMORY_TYPES`. Each LLM-extracted `MemoryUnit` now records
  `prompt_version` in metadata for future A/B and regression tracking.
- **`nanomem.service.facade.ControlFacade`** — narrow read-only view
  over `NanoMemControlService` for the HTTP/manager layer. Closes the
  layering violation where `server/manager.py` imported control
  internals directly.
- **`nanomem.factory.nanomem_service_with_defaults`** — explicit, public
  entry point for the dependency-light local default construction.
- **`.claude/skills/architecture-refactor/SKILL.md`** — reusable
  architecture-refactor workflow skill (audit → diagnose → propose →
  sequence → execute-with-review).
- **Baseline tests** for previously untested subpackages (`heuristic`,
  `hybrid`, `render`, `ranking`, `control`, `maintenance`, `adapters`),
  plus tests for the new `errors`, `protocols`, `prompts`, and `facade`
  surfaces. ~50 new tests.

### Changed (BREAKING)

- **`nanomem.contracts`** is now a package, not a module. `from
  nanomem.contracts import X` import sites continue to work via the
  package `__init__.py` re-export. Sub-modules: `core`, `requests`,
  `results`, `selectors`, `logs`. Direct imports of
  `nanomem.contracts.<symbol>` still work; new code may target the
  sub-modules.
- **`nanomem.policies`** is now a package. `policies/scope.py` holds
  `scope_matches()` and `namespace_matches()`. The historical names
  remain importable from `nanomem.policies` via `__init__`.
- **`nanomem.embeddings`** has moved to **`nanomem.index.embeddings`**.
  The old path is preserved as a deprecation shim that emits
  `DeprecationWarning`. The shim will be removed in a future alpha.

### Changed (non-breaking)

- 25 ad-hoc `raise ValueError(...)` / `raise RuntimeError(...)` sites
  across `service/`, `factory.py`, `extraction/llm.py`,
  `index/lancedb.py`, `embeddings/hashing.py`, and `maintenance/` now
  raise the appropriate `NanoMemError` subclass. `except ValueError`
  callers keep working because the input-validation classes
  multi-inherit from `ValueError`.
- `mcp/server.py:_read` now uses `serde.read_result_to_json` instead of
  `dataclasses.asdict` for consistency with the HTTP server path.
- `tui/__init__.py` and `integrations/__init__.py` now carry docstrings
  documenting their experimental status and layered relationship to
  `adapters/`.

### Deprecated

- Importing from `nanomem.embeddings.*` — emits `DeprecationWarning`.
  Use `nanomem.index.embeddings.*` instead. **The shim will be removed
  in v0.3.0** (see `nanomem.embeddings.__deprecated_removal__`).
- Calling `NanoMemService()` with no arguments to get default
  dependencies. The pattern still works, but v0.3 will require explicit
  injection of `store`, `index`, `extractor`, etc. Use
  `nanomem.factory.nanomem_service_with_defaults()` to get the same
  defaults via a stable, documented surface.

### Migration notes

- **Catching exceptions:** existing `except ValueError` blocks keep
  working for input-validation errors. Prefer `except NanoMemError` (or
  a specific subclass) in new code.
- **Embedding imports:** replace `from nanomem.embeddings import X`
  with `from nanomem.index.embeddings import X` to avoid the
  deprecation warning.
- **Service construction:** if you call `NanoMemService()` directly,
  consider switching to `nanomem.factory.nanomem_service_with_defaults()`
  before v0.3 lands.

### Process notes

This release was produced by a 10-batch refactor driven by the
`architecture-refactor` skill. Each batch was committed independently;
the full diff can be replayed via `git log v0.1.0..v0.2.0a1`. Pre-existing
test failures in `tests/integrations/test_hooks.py` are unrelated to this
work (verified by stash-pop check on baseline `main`).

## [0.1.0]

Initial alpha release. See `readme.md` and `docs/` for the design
boundary, capture/read pipelines, and storage/index strategy.
