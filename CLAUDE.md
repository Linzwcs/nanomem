# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

Run from the repository root.

### Python (core package)

```bash
python -m pip install -e ".[dev]"            # install package + test deps
python -m pip install -e ".[dev,lancedb]"    # add optional LanceDB index backend

python -m pytest                              # full suite (auto picks up src/ via pyproject pythonpath)
python -m pytest tests/service/test_capture_read.py            # single file
python -m pytest tests/service/test_capture_read.py::test_x    # single test
python -m pytest tests/index/test_lancedb_integration.py       # requires `[lancedb]` extra

python -m compileall -q src/nanomem           # compile check (matches CI)
```

If the package is not installed, the CLI/server/MCP entry points are also reachable via modules:

```bash
PYTHONPATH=src python -m nanomem.cli --help
PYTHONPATH=src python -m nanomem.server --help
PYTHONPATH=src python -m nanomem.mcp --help
```

When installed, prefer the console scripts: `nanomem`, `nanomem-server`, `nanomem-mcp`, `nanomem-agent-hook`.

CI matrix: Python 3.10 / 3.11 / 3.12 (Ubuntu) — runs `compileall` then `pytest`.

### Manager UI (React/Vite, in `manager-ui/`)

The web manager has a Python-served bundled asset path *and* a separate React/Vite source tree. The Vite build emits compiled assets back into the Python package at `src/nanomem/ops/manager_assets/assets/`.

```bash
cd manager-ui
npm install
npm run dev        # vite dev server, proxies /manager/api → 127.0.0.1:8765
npm run build      # tsc + vite build → ../src/nanomem/ops/manager_assets/assets/
npm test           # vitest
```

Run `nanomem-server` in another terminal so the proxied API is reachable during dev.

### Local server quick check

```bash
nanomem-server --config nanomem.json --host 127.0.0.1 --port 8765
curl http://127.0.0.1:8765/v1/health
# Manager UI:
open http://127.0.0.1:8765/manager
```

## Architecture

NanoMem is a **long-term personal memory backend** for AI agent harnesses. The agent already has the workspace, files, repo, logs, and tools — NanoMem stores only the durable personal facts that don't belong in any of those (preferences, corrections, habits, background, agent-interaction events).

### Layered data model

```
Session         groups capture streams
Dialogue        archived user-visible messages (the capture source of truth)
DialogueWindow  open buffer + extraction lifecycle (open → sealed → extracted)
MemoryUnit      fine-grained durable personal fact (the storage unit)
IndexHit        derived retrieval candidate
PackedContext   final rendered evidence for the agent prompt
```

`Dialogue`/`DialogueWindow` do **not** own memory scope. The first object carrying `owner_id` + `namespace` is the extracted `MemoryUnit`. Indexes are derived data and can always be rebuilt from the store.

### Runtime flow

```
server / mcp / sdk
    ↓
NanoMemService (orchestration)
    ├── CapturePipeline → Extractor → Store + Index
    └── ReadPipeline    → Index → Store → Ranker → Renderer → PackedContext
```

The architecture rule of thumb (from `docs/architecture-overview.md`):

```
server -> service -> store/index/extraction/ranking/render -> contracts
```

The service layer owns orchestration. Stores, indexes, extractors, rankers, renderers are replaceable capabilities behind small interfaces — they should not decide capture/read behavior. Server code must not reach into concrete store/index internals; adapters must not bypass `NanoMemService`.

### Public agent surface is intentionally tiny

```
HTTP:   GET /v1/health,  POST /v1/capture,  POST /v1/flush,  POST /v1/read
MCP:    nanomem_read     (read-only — writes go through capture/SDK/HTTP, never MCP)
SDK:    NanoMemClient / AsyncNanoMemClient (sync + async HTTP clients)
CLI:    administrative — stats, list, logs, backup, export, retention, reindex, dashboard, install-codex-hooks
```

`/manager` and `/manager/api/*` are **control-plane only** — never expose them as agent-facing tools or to untrusted networks. Likewise, MCP must not expose backup/export/retention/reindex.

### Source layout (`src/nanomem/`) — v0.3 horizontal layering

Six layers; each may only import from layers below it.
`tools/check_layering.py` + `tests/test_layering.py` enforce the rule.

```
core/                    foundations (stdlib only)
  contracts/             frozen dataclasses for public types
  errors.py              NanoMemError hierarchy
  ids.py / time.py       ID + timestamp helpers
  serde.py               dict ↔ contract conversion
  policies/              scope and namespace matching
  config.py              config schema + loaders

pipeline/                paper-axis-aligned capabilities
  representation/        memory unit extraction (heuristic, llm/*)
  storage/               durable fact store (sqlite)
  retrieval/             find candidates
    indexes/             lexical, dense, hybrid, lancedb
    embeddings/          hashing (default), openai_compatible
    ranking/             relevance + recency (relevance_recency.py)
  utilization/           pack ranked units under token budget
                         (evidence_context.py)

service/                 pipeline orchestration
  core.py / async_core.py  NanoMemService (sync + async)
  capture.py / read.py     pipeline implementations
  facade.py                ControlFacade for transports/http
  factory.py               config-driven construction
  control/                 control-plane operations (stats, backup,
                           export, retention, reindex)

transports/              wire formats
  http/                  stdlib server (v1 data plane + manager UI)
  mcp/                   stdio MCP server (read-only)
  sdk/                   sync + async HTTP clients

ops/                     operator-facing tools
  maintenance/           composed control workflows
  cli/                   `nanomem` command-line
  tui/                   terminal dashboard
  manager_assets/        bundled HTML/CSS/JS for manager UI

hosts/                   external-harness integration
  adapters/              AgentMemoryAdapter + per-host adapters
                         (Codex, OpenClaw, NanoBot, MCP)
  plugins/               agent hook runner (`nanomem-agent-hook`),
                         Codex install helper
```

Layering rule (machine-enforced):

```
hosts/      may import service, transports, ops, pipeline, core
ops/        may import service, pipeline, core
transports/ may import service, pipeline, core
service/    may import pipeline, core
pipeline/   may import core
core/       only stdlib
```

Two documented exceptions (marked `# layering-exception:` on the
import line):
- `service/factory.py` constructs ops/maintenance — composition root.
- `ops/cli/main.py` invokes `install_codex_hooks` from `hosts/plugins/codex`.

Tests in `tests/` mirror the package areas they cover.

## Conventions That Matter

- **Append-only fact units.** MemoryUnits are durable, scope-tagged, third-person, evidence-grounded. Capture must not ingest hidden reasoning, raw tool output, complete chat archives, project docs, or multimodal raw assets.
- **Read returns evidence, not a profile.** Rendered context preserves timestamps and dialogue refs so the downstream agent can reason over conflicts and time. NanoMem must not silently synthesize a canonical user view.
- **`flush` is window control, not a write.** It seals pending dialogue buffers so extracted units become searchable. Because windows don't own scope, flushing pending state requires both `session_id` and extraction `scope`.
- **NanoMem does not implement ANN.** The local `dense` index is intentionally bounded (scope-filter first, then scan up to `index.dense_scan_limit`). For real ANN, use the LanceDB adapter or a future Postgres + pgvector adapter — never expand SQLite into a vector engine via JSON scans.
- **Local data dir.** Default state lives under `.nanomem/` (db, lancedb/, backups/, exports/). Never commit it. Bind the HTTP server to `127.0.0.1`.
- **Style.** Python 3.10+, `from __future__ import annotations`, frozen dataclasses, protocols / ABCs, explicit serialization helpers in `core/serde.py`. Public contracts stay in `core/contracts/`; cross-module construction stays in `service/factory.py`.
- **Tests.** `pytest` with deterministic fixtures — temporary SQLite DBs and hashing embeddings; avoid network-backed providers. Mirror package paths in test names. Add regressions for store migrations, schema parsing, ranking, and CLI/server edge cases when changing those areas.
- **Status: alpha.** Public contracts may still change. The README's *Feature Status* table is the source of truth for what's stable vs. in transition vs. planned.

## Documentation Map

For deeper context (especially before non-trivial changes):

- `readme.md` — first-run guide and project summary.
- `AGENTS.md` — repository style/test/PR guidelines.
- `docs/system-design.md` — top-level product + architecture design.
- `docs/nanomem-product-rfc.md` — product boundary and memory semantics (what to store / not store).
- `docs/agent-memory-positioning.md` — how different agent harnesses should read/write.
- `docs/architecture-overview.md` — diagrams, runtime layout, store/index split.
- `docs/index-backends.md` — in-memory vs. LanceDB vs. Postgres/pgvector strategy.
- `docs/nanomem-code-architecture.md` — module-level implementation architecture.
- `docs/manager/README.md` — web manager and control-plane design.
- `docs/plugins/` — Codex and Claude Code plugin docs.
- `docs/reports/request-response-examples.md` — complete API examples (kept in sync via `tests/docs/`).
