# Changelog

All notable changes to this project will be documented in this file.

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
