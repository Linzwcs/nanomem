# Changelog

All notable changes to this project will be documented in this file.

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
