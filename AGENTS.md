# Repository Guidelines

## Project Structure & Module Organization

NanoMem uses a Python `src/` layout. Core package code lives in `src/nanomem/`.
Important subpackages include `service/` for capture/read orchestration, `store/` for persistence, `index/` and `embeddings/` for retrieval, `extraction/` for memory extraction, `server/` for the HTTP API, `mcp/` for MCP integration, `cli/` for command-line administration, and `adapters/` for external agent integrations. Design notes and product context live in `docs/`. No test directory or package metadata is currently present; add tests under `tests/` when introducing behavior changes.

## Build, Test, and Development Commands

Run commands from the repository root.

- `PYTHONPATH=src python -m nanomem.cli --help`: show CLI commands.
- `PYTHONPATH=src python -m nanomem.server --help`: inspect server startup options.
- `PYTHONPATH=src python -m nanomem.mcp --help`: inspect MCP entry point options.
- `PYTHONPATH=src python -m pytest`: run the test suite once tests are added.

Because this checkout has no `pyproject.toml`, install dependencies and tooling in a local virtual environment before adding new commands. If you introduce package metadata, document the replacement commands here.

## Coding Style & Naming Conventions

Use Python 3 type annotations and keep modules focused on one responsibility. The existing code uses 4-space indentation, `from __future__ import annotations`, dataclasses, protocols/abstract base classes, and explicit serialization helpers. Prefer clear snake_case names for functions, modules, and variables; use PascalCase for classes such as `NanoMemService` and `SQLiteMemoryUnitStore`. Keep public contracts in `contracts.py`, configuration in `config.py`, and cross-module construction in `factory.py`.

## Testing Guidelines

Use `pytest` for new tests. Mirror package paths in test names, for example `tests/service/test_core.py` for `src/nanomem/service/core.py`. Favor deterministic unit tests with temporary SQLite databases and hashing embeddings over network-backed providers. Add regression tests for store migrations, request schema parsing, ranking behavior, and CLI/server edge cases when those areas change.

## Commit & Pull Request Guidelines

This checkout does not include Git history, so use concise imperative commit subjects such as `Add SQLite migration tests` or `Fix capture request validation`. Pull requests should include a short problem summary, the chosen implementation, test evidence, and any config or migration impact. Link related issues when available and include example CLI/API output for user-visible behavior changes.

## Security & Configuration Tips

Do not commit local databases, exported memory payloads, API keys, or `.env` files. Keep provider credentials in environment variables or ignored local config files. Use temporary paths for backups and export tests, and avoid logging raw memory content unless the behavior is explicitly under test.
