# NanoMem

[![CI](https://github.com/Linzwcs/nanomem/actions/workflows/ci.yml/badge.svg)](https://github.com/Linzwcs/nanomem/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

NanoMem is a local-first long-term personal memory backend for AI agents.

It is built for agent harnesses that already read files, search repos, run
tools, inspect git, and use workspace-specific context. NanoMem keeps the part
that does not belong in a repo: durable, cross-session, user-specific personal
memory.

```text
The agent reads the workspace. NanoMem helps it remember the user.
```

Status: alpha. The core local backend is implemented and tested. Public
contracts may still change before a stable release.

## Why This Design

NanoMem is not a generic "store everything" memory system. Its architecture is
the production realization of an evaluated research principle:

> Personal memory helps an agent only through the bounded memory block that
> reaches the LLM at answer time. The right metric is the **density of useful
> evidence in that final rendered block**, not retrieval recall in isolation.

This claim — and the design choices it implies — was studied in the companion
paper *Long-Term Personal Memory Under Budget: An Evidence-Density Principle*
(initial experiment code in
[nanomem-exp](../nanomem-exp), branch `initial-experiment-code`). Two design
axes were varied under a fixed post-render token budget on LoCoMo and
LongMemEval:

- **Representation**: how dialogue is converted into memory — interaction
  pairs, chunks, summaries, or **atomic fact records**;
- **Utilization**: how retrieved units are ordered, merged, and packed into
  the prompt — `default`, `merge`, `time`, `time+merge`.

The controlled finding: **fact-style records + chronological merging
(`Fact + Time+Merge`)** are the strongest combination across budgets. NanoMem's
production stack (`extraction/` produces atomic facts, `render/` packs ranked
facts with timestamps under a token budget) is the same configuration.

### Validation Snapshot

Protocol-aligned numbers from the paper draft (see
[nanomem-exp/README.md](../nanomem-exp) on the `initial-experiment-code`
branch). External rows use different reporting protocols and are shown as
references.

LoCoMo system comparison (Overall, ↑ better):

| Method        | Tokens | Overall   |
| ------------- | -----: | --------: |
| Mem0          |   1.0k |     64.20 |
| MemOS         |   2.5k |     80.76 |
| Zep           |   1.4k |     85.22 |
| EverMemOS     |   2.3k | **93.05** |
| **Ours (1.0k)** | 1.75k | **92.92** |

LongMemEval system comparison (Overall, ↑ better):

| Method          | Tokens | Overall   |
| --------------- | -----: | --------: |
| Mem0            |   1.1k |     66.40 |
| MemOS           |   1.4k |     77.80 |
| EverMemOS       |   2.8k |     83.00 |
| **Ours (1.0k)** | 1.75k |     87.40 |
| **Ours (2.0k)** | 2.75k | **89.20** |

Controlled 1000-token budget (mean of three runs):

| Dataset     | Best controlled setting | Overall   |
| ----------- | ----------------------- | --------: |
| LoCoMo      | Fact + Time+Merge       | **75.11** |
| LongMemEval | Fact + Time+Merge       | **84.07** |

Reproduction configs and exporters live in `nanomem-exp` on the
`initial-experiment-code` branch. This repository is the production backend
that those experiments validate.

## Product Boundary

```text
workspace facts        stay in files, repos, logs, artifacts, and external systems
NanoMem MemoryUnits    durable personal facts with scope, time, and dialogue refs
indexes                derived data, always rebuildable from the store
read                   returns timestamped evidence, not a canonical user profile
agent surface          stays small: capture and read
```

Good fits:

- coding/local agents such as Codex, Claude Code, and OpenClaw-like runtimes;
- personal assistants that need durable user preferences and corrections;
- MCP hosts that need a small read-only memory sidecar;
- local-first deployments where SQLite is enough as the source of truth.

Non-goals: workspace search replacement, document ingestion or RAG over
project files, task database, run log store, raw event sourcing, canonical
user-profile maintenance.

## Feature Status

| Area              | Status        | Notes |
| ----------------- | ------------- | ----- |
| Core contracts    | In transition | target model: `Session`, `Dialogue`, `DialogueWindow`, `MemoryUnit` |
| Local store       | Implemented   | SQLite fact store with migrations and operation logs |
| Capture pipeline  | Implemented   | Heuristic extractor by default; LLM extractor optional |
| Read pipeline     | Implemented   | retrieval, ranking, evidence rendering, token budget |
| HTTP API          | Implemented   | `/v1/health`, `/v1/capture`, `/v1/flush`, `/v1/read` |
| Python SDK        | Implemented   | sync and async HTTP clients |
| MCP server        | Implemented   | stdio server exposing read-only `nanomem_read` |
| CLI/control plane | Implemented   | stats, list, backup, export, retention, reindex, dashboard, Codex hook install |
| Web manager       | Local alpha   | bundled static manager and React/Vite work-in-progress |
| Index backends    | Local alpha   | lexical, dense, hybrid, optional LanceDB |
| Agent plugins     | Experimental  | Codex project hooks plus Codex and Claude Code plugin skeletons |
| Managed deployment| Planned       | Postgres + pgvector is a future path, not the current default |

## Quick Start

Install locally from the repository root:

```bash
python -m pip install -e ".[dev]"
nanomem --help
nanomem-server --help
nanomem-mcp --help
```

Create `nanomem.json`:

```json
{
  "data_dir": ".nanomem",
  "store": { "backend": "sqlite" },
  "index": { "backend": "dense" },
  "extraction": { "backend": "heuristic" },
  "read": {
    "default_recency_policy": "balanced",
    "default_max_units": 10
  }
}
```

Start the local HTTP sidecar and check health:

```bash
nanomem-server --config nanomem.json --host 127.0.0.1 --port 8765
curl http://127.0.0.1:8765/v1/health
```

Capture one user-visible turn:

```bash
curl -X POST http://127.0.0.1:8765/v1/capture \
  -H 'Content-Type: application/json' \
  -d '{
    "scope": {"owner_id": "demo-user", "namespace": "personal"},
    "dialogue": {
      "messages": [
        {
          "role": "user",
          "speaker_id": "user:demo-user",
          "content": "I prefer concise Chinese answers. Please remember that I usually want architecture first, then code.",
          "timestamp": "2026-05-19T10:00:00+08:00"
        }
      ],
      "occurred_at": "2026-05-19T10:00:00+08:00",
      "metadata": {"host": "quickstart"}
    },
    "capture_time": "2026-05-19T10:00:05+08:00"
  }'
```

Read relevant memory under a token budget:

```bash
curl -X POST http://127.0.0.1:8765/v1/read \
  -H 'Content-Type: application/json' \
  -d '{
    "owner_id": "demo-user",
    "namespaces": ["personal"],
    "query": "answer style architecture first",
    "query_time": "2026-05-19T10:10:00+08:00",
    "max_units": 3,
    "context_budget_tokens": 512
  }'
```

The response contains ranked units and a packed, timestamped context block:

```json
{
  "context": {
    "text": "Relevant memory units:\n- [2026-05-19T10:00:00+08:00, namespace=personal] Please remember that I usually want architecture first, then code.",
    "token_count": 42,
    "unit_count": 1
  }
}
```

Open the local manager while the server is running:

```text
http://127.0.0.1:8765/manager
```

The manager is a control-plane UI for inspecting memory units, dialogues,
operation logs, retrieval previews, and index health. Do not expose
`/manager` or `/manager/api/*` as agent-facing tools or to untrusted networks.

Full request/response examples:
[docs/reports/request-response-examples.md](docs/reports/request-response-examples.md).

## Core Model

NanoMem separates raw dialogue, window control, durable memory, and retrieval:

```text
Session         groups related capture streams
Dialogue        archived user-visible messages (capture source of truth)
DialogueWindow  open buffer + extraction lifecycle
MemoryUnit      fine-grained durable personal fact (the storage unit)
IndexHit        derived retrieval candidate
PackedContext   rendered evidence block for an agent prompt
```

`Dialogue` and `DialogueWindow` do not own memory scope. The first object
carrying `owner_id` and `namespace` is the extracted `MemoryUnit`. Indexes are
derived data and can always be rebuilt from the store. Rendered context is
the final agent input — and, per the validation work above, the place where
evidence density actually matters.

Preferred memory style — third-person, evidence-grounded, timestamped:

```text
The user said they prefer concise Chinese answers.
The user corrected the agent not to auto-commit code.
The agent auto-committed code and the user reacted negatively.
```

Avoid first-person commands and project-style assertions:

```text
Do not auto-commit code.            ← hidden instruction, not evidence
Always answer in Chinese.           ← same problem
This repo uses pytest.              ← workspace fact, belongs in CLAUDE.md/README
```

The downstream agent should reason over evidence, time, scope, and
conflicts. NanoMem must not silently synthesize a canonical user profile.

## What To Store / Not To Store

Store durable, user-related personal facts:

- user preferences and communication style;
- user corrections to agent behavior;
- stable cross-project engineering habits;
- personal background and relationship facts;
- user-relevant events that matter later;
- agent-interaction events that change future collaboration;
- personal facts extracted from discussions of multimodal resources.

Do not store:

- README, ADRs, code, configuration, or project docs;
- raw PDFs, images, audio, video, screenshots, or datasets;
- CI logs, build output, raw tool output, or hidden reasoning;
- current task plans, scratchpads, issue state, or run logs;
- complete chat archives;
- facts the agent can reliably read again from workspace or source systems.

Rule of thumb:

```text
If the agent can read it again from the workspace, repo, logs, object storage,
or a business system, do not put it in NanoMem.

If it is a cross-session personal fact that changes how the agent should
understand or collaborate with the user, put it in NanoMem.
```

## Interfaces

The agent-facing surface is intentionally small:

```text
capture
read
```

`flush` is a session/window control operation, not a write. It seals pending
dialogue buffers so extracted units become searchable. Because windows do not
carry memory scope, flushing pending state requires both `session_id` and
extraction `scope`. Admin, backup, export, retention, delete, reindex, and
raw dialogue inspection belong to CLI or control-plane surfaces, not agent
tools.

### HTTP

```text
GET  /v1/health
POST /v1/capture
POST /v1/flush
POST /v1/read
```

Capture without `session_id` treats the payload as a complete dialogue and
extracts immediately. Capture with `session_id` appends raw messages to that
session's open dialogue window; call `/v1/flush` when a session pauses,
exits, or should become searchable before the token window fills.

### Python SDK

```python
from nanomem import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    NanoMemClient,
    ReadRequest,
)

client = NanoMemClient("http://127.0.0.1:8765")

client.capture(
    CaptureRequest(
        scope=MemoryScope(owner_id="demo-user", namespace="personal"),
        dialogue=CaptureDialogue(
            occurred_at="2026-05-19T10:00:00+08:00",
            messages=(
                DialogueMessage(
                    role="user",
                    content="I prefer concise Chinese answers.",
                    timestamp="2026-05-19T10:00:00+08:00",
                ),
            ),
        ),
        capture_time="2026-05-19T10:00:05+08:00",
    )
)

result = client.read(
    ReadRequest(
        owner_id="demo-user",
        namespaces=("personal",),
        query="answer language preference",
        query_time="2026-05-19T10:01:00+08:00",
        max_units=5,
    )
)

print(result.context.text)
```

`AsyncNanoMemClient` mirrors the same surface for async hosts.

### MCP

Run the stdio MCP server:

```bash
nanomem-mcp --config nanomem.json
```

MCP exposes `nanomem_read` only. Writes go through hook capture, the SDK, or
the HTTP API — never through model-selected MCP tools. Control-plane actions
(backup, export, retention, reindex) also stay out of the MCP surface.

### CLI

The CLI manages the local SQLite database and maintenance workflows:

```bash
nanomem stats --config nanomem.json
nanomem list --config nanomem.json --limit 20
nanomem logs --config nanomem.json
nanomem migrations --config nanomem.json
nanomem integrity-check --config nanomem.json
nanomem reindex --config nanomem.json
nanomem dashboard --config nanomem.json

nanomem backup  --config nanomem.json --output .nanomem/backups/backup.db
nanomem export  --config nanomem.json --output .nanomem/exports/export.json
nanomem retention-preview      --config nanomem.json --before 2026-01-01T00:00:00+00:00
nanomem log-retention-preview  --config nanomem.json --before 2026-01-01T00:00:00+00:00
```

Without the package installed, use module entry points from the repo root:

```bash
PYTHONPATH=src python -m nanomem.cli --help
PYTHONPATH=src python -m nanomem.server --help
PYTHONPATH=src python -m nanomem.mcp --help
```

## Configuration

Default local state lives under one data directory:

```text
.nanomem/
  nanomem.db
  lancedb/
  backups/
  exports/
```

Supported config values:

| Key                         | Values                                       |
| --------------------------- | -------------------------------------------- |
| `store.backend`             | `sqlite`                                     |
| `index.backend`             | `lexical`, `dense`, `hybrid`, `lancedb`      |
| `index.embedding.backend`   | `hashing`, `openai_compatible`               |
| `extraction.backend`        | `heuristic`, `llm`                           |
| `read.default_recency_policy` | `recent`, `balanced`, `historical`         |

The default local setup is dependency-light:

- SQLite is the fact store;
- `dense` is the default index backend with bounded scope-filtered scan;
- deterministic local hashing is the default embedding model;
- `heuristic` is the default extractor;
- `index.rebuild_on_startup = true` rebuilds derived indexes from SQLite.

Use environment variables for provider credentials. Do not put API keys in
config files committed to the repository.

### Optional LanceDB

For larger-scale local ANN, install the optional dependency:

```bash
python -m pip install -e ".[dev,lancedb]"
```

Configure the local vector index:

```json
{
  "index": {
    "backend": "lancedb",
    "path": ".nanomem/lancedb",
    "table": "memory_units",
    "distance_type": "cosine"
  }
}
```

LanceDB stores retrieval fields and embeddings. SQLite remains the source of
truth for `MemoryUnit` and `Dialogue`.

NanoMem itself does not implement ANN. The in-memory `dense` index is
deliberately bounded (scope-filter first, then scan up to
`index.dense_scan_limit`). For real ANN, use LanceDB or a future Postgres +
pgvector adapter — never expand SQLite into a vector engine via JSON scans.

## Agent Integrations

NanoMem follows a simple lifecycle:

```text
before_turn:
  agent reads workspace/tools
  agent calls NanoMem.read for personal evidence

after_turn:
  agent sends user-visible dialogue to NanoMem.capture
```

Repo-local plugin skeletons:

```text
.agents/plugins/marketplace.json
plugins/nanomem-codex/
plugins/nanomem-claude-code/
```

Hook runner examples:

```bash
nanomem-agent-hook spool   --host codex
nanomem-agent-hook read    --host codex
nanomem-agent-hook capture --host codex
nanomem-agent-hook spool   --host claude-code
nanomem-agent-hook read    --host claude-code
nanomem-agent-hook capture --host claude-code
```

For Codex, install project-level hooks:

```bash
nanomem install-codex-hooks --project-dir .

export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

Plugin-bundled Codex hooks remain an opt-in packaging path and should be
validated separately. Plugin docs:

- [docs/plugins/README.md](docs/plugins/README.md)
- [docs/plugins/codex.md](docs/plugins/codex.md)
- [docs/plugins/codex-installation.md](docs/plugins/codex-installation.md)
- [docs/plugins/claude-code.md](docs/plugins/claude-code.md)

## Project Layout

`src/nanomem/` is organized as **6 horizontal layers**, each only
importing from layers below it. The structure mirrors the experimental
axes in the companion paper. A `tools/check_layering.py` script and a
`tests/test_layering.py` regression gate enforce the rule.

```text
src/nanomem/
  core/                  foundations (stdlib only)
    contracts/           frozen dataclasses for the public surface
    errors.py            NanoMemError hierarchy
    ids.py, time.py      ID + timestamp helpers
    serde.py             dict ↔ contract conversion
    policies/            scope / namespace matching
    config.py            config schema + loaders

  pipeline/              paper-axis-aligned capabilities
    representation/      heuristic + LLM extraction → atomic fact units
    storage/             SQLite fact store
    retrieval/
      indexes/           lexical, dense, hybrid, LanceDB
      embeddings/        hashing (default), openai_compatible
      ranking/           relevance + recency (relevance_recency.py)
    utilization/         budget-aware evidence rendering
                         (evidence_context.py)

  service/               pipeline orchestration
    core.py / async_core.py
    capture.py / read.py
    facade.py            ControlFacade for the manager UI
    factory.py           config-driven construction
    control/             control-plane operations

  transports/            wire formats for agent harnesses
    http/                stdlib server (v1 data plane + manager UI)
    mcp/                 stdio MCP server (read-only)
    sdk/                 sync + async HTTP clients

  admin/                 operator-facing tools
    cli/                 `nanomem` command-line
    tui.py               terminal dashboard
    manager_ui/          bundled HTML/CSS/JS for the manager UI

  hosts/                 external-harness integration
    adapters/            AgentMemoryAdapter + MCP adapter
    plugins/             hook runner, Codex install helper

manager-ui/              React/Vite manager source (builds into
                         src/nanomem/admin/manager_ui/)
tools/                   maintenance scripts (check_layering.py)
docs/                    product, architecture, manager, plugin docs
tests/                   pytest regression tests
```

Layering rule (machine-enforced):

```text
hosts/      may import service, transports, admin, pipeline, core
admin/      may import service, pipeline, core
transports/ may import service, pipeline, core
service/    may import pipeline, core
pipeline/   may import core
core/       only stdlib
```

The service layer owns orchestration. Stores, indexes, extractors, rankers,
and renderers are replaceable capabilities behind small interfaces — they
should not decide capture/read behavior. Server code must not import concrete
store/index internals; adapters must not bypass `NanoMemService`.

## Development

Install dev dependencies and run the test suite:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Run a focused LanceDB integration test after installing the extra:

```bash
python -m pip install -e ".[dev,lancedb]"
python -m pytest tests/index/test_lancedb_integration.py
```

CI runs `compileall` and `pytest` on Python 3.10, 3.11, and 3.12.

For benchmark reproduction (LoCoMo, LongMemEval, paired comparisons,
budget curves), use the experiment platform in
[`nanomem-exp`](../nanomem-exp), branch `initial-experiment-code`. That
repository is the artifact-first evaluation harness; this repository is the
production backend.

## Security And Data

NanoMem stores personal memory data.

- Do not commit `.nanomem/`, local databases, exports, backups, `.env`, or
  API keys.
- Bind the HTTP server to `127.0.0.1` for local use.
- Do not expose `/manager` or `/manager/api/*` to untrusted networks.
- Keep raw workspace files, logs, tool output, and multimodal assets outside
  NanoMem.
- Use backup/export/retention commands with temporary paths in tests.
- Enable hook debug payloads only temporarily; they may contain prompt or
  transcript metadata.

## Documentation Map

Design and product context:

- [docs/system-design.md](docs/system-design.md) — top-level product and architecture design.
- [docs/nanomem-product-rfc.md](docs/nanomem-product-rfc.md) — product boundary and memory semantics.
- [docs/agent-memory-positioning.md](docs/agent-memory-positioning.md) — agent read/write guidance.
- [docs/architecture-overview.md](docs/architecture-overview.md) — diagrams, runtime layout, store/index split.
- [docs/index-backends.md](docs/index-backends.md) — in-memory, LanceDB, and Postgres/pgvector strategy.
- [docs/nanomem-code-architecture.md](docs/nanomem-code-architecture.md) — module-level implementation architecture.
- [docs/manager/README.md](docs/manager/README.md) — web manager and control-plane design.
- [docs/reports/request-response-examples.md](docs/reports/request-response-examples.md) — complete API examples.

Companion evaluation work:

- [`nanomem-exp`](../nanomem-exp), branch `initial-experiment-code` —
  experiment configs, runners, and result tables for *Long-Term Personal
  Memory Under Budget: An Evidence-Density Principle*.

## License

MIT. See package metadata in [pyproject.toml](pyproject.toml).
