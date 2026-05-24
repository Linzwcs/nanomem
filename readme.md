# NanoMem

[![CI](https://github.com/Linzwcs/nanomem/actions/workflows/ci.yml/badge.svg)](https://github.com/Linzwcs/nanomem/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

NanoMem is a local-first long-term personal memory backend for AI agents.

It is built for agent harnesses that can already read files, search repos, run
tools, inspect git, and use workspace-specific context. NanoMem keeps the part
that does not belong in a repo: durable, cross-session, user-specific personal
memory.

```text
The agent reads the workspace. NanoMem helps it remember the user.
```

Status: alpha. The core local backend is implemented and tested, but public
contracts may still change before a stable release.

## Why NanoMem

Most agent memory systems drift toward "store everything": chat transcripts,
documents, code snippets, logs, search results, preferences, and task state in
one retrieval pool. That makes source of truth unclear and lets large workspace
artifacts bury the small personal facts that matter across sessions.

NanoMem takes the opposite boundary:

- workspace facts stay in files, repos, logs, artifacts, and external systems;
- NanoMem stores fine-grained personal `MemoryUnit`s;
- indexes are derived and rebuildable;
- `read` returns timestamped evidence, not a canonical user profile;
- the agent-facing API stays small: `capture` and `read`.

Good fits:

- coding/local agents such as Codex, Claude Code, and OpenClaw-like runtimes;
- personal assistants that need durable user preferences and corrections;
- MCP hosts that need a small memory sidecar;
- local-first deployments where SQLite is enough as the source of truth.

Non-goals:

- workspace search replacement;
- document ingestion or RAG over project files;
- task database, scratchpad, or run log store;
- raw event sourcing;
- canonical truth maintenance for user profiles.

## Feature Status

| Area | Status | Notes |
| --- | --- | --- |
| Core contracts | In transition | target model: `Session`, `Dialogue`, `DialogueWindow`, `MemoryUnit` |
| Local store | Implemented | SQLite fact store with migrations and operation logs |
| Capture pipeline | Implemented | Heuristic extractor by default; LLM extractor optional |
| Read pipeline | Implemented | retrieval, ranking, evidence rendering, token budget |
| HTTP API | Implemented | `/v1/health`, `/v1/capture`, `/v1/flush`, `/v1/read` |
| Python SDK | Implemented | sync and async HTTP clients |
| MCP server | Implemented | stdio server exposing read-only `nanomem_read` |
| CLI/control plane | Implemented | stats, list, backup, export, retention, reindex, dashboard, Codex hook install |
| Web manager | Local alpha | bundled static manager and React/Vite work-in-progress |
| Index backends | Local alpha | lexical, dense, hybrid, optional LanceDB |
| Agent plugins | Experimental | Codex project hooks plus Codex and Claude Code plugin skeletons |
| Managed deployment | Planned | Postgres + pgvector is a future path, not current default |

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
  "store": {
    "backend": "sqlite"
  },
  "index": {
    "backend": "dense"
  },
  "extraction": {
    "backend": "heuristic"
  },
  "read": {
    "default_recency_policy": "balanced",
    "default_max_units": 10
  }
}
```

Start the local HTTP sidecar:

```bash
nanomem-server --config nanomem.json --host 127.0.0.1 --port 8765
```

Check health:

```bash
curl http://127.0.0.1:8765/v1/health
```

Write a memory from user-visible dialogue:

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

Read relevant memory:

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

The response includes ranked units and a packed context string similar to:

```json
{
  "context": {
    "text": "Relevant memory units:\n- [2026-05-19T10:00:00+08:00, namespace=personal] Please remember that I usually want architecture first, then code.",
    "token_count": 42,
    "unit_count": 1
  },
  "ranked_units": [
    {
      "rank": 1,
      "score": 0.38,
      "unit": {
        "memory_type": "background",
        "text": "Please remember that I usually want architecture first, then code.",
        "timestamp": "2026-05-19T10:00:00+08:00"
      }
    }
  ]
}
```

Open the local manager while the server is running:

```text
http://127.0.0.1:8765/manager
```

The manager is a control-plane UI for inspecting memory units, dialogues,
operation logs, retrieval preview, and index health. Do not expose manager or
control endpoints as agent-facing tools.

## Core Model

NanoMem separates raw dialogue, window control, durable memory, and retrieval:

```text
Session         = groups related capture streams
Dialogue        = archived user-visible messages
DialogueWindow  = buffering and extraction lifecycle
MemoryUnit      = fine-grained durable personal fact
IndexHit        = derived retrieval candidate
PackedContext   = rendered evidence for an agent prompt
```

Capture source is user-visible dialogue. `Dialogue` and `DialogueWindow`
do not own memory scope. The first object with `owner_id` and `namespace` is
the extracted `MemoryUnit`. Indexes are derived data and can be rebuilt.
Rendered context is the final prompt input for an agent.

Preferred memory style:

```text
The user said they prefer concise Chinese answers.
The user corrected the agent not to auto-commit code.
The agent auto-committed code and the user reacted negatively.
```

Avoid turning memory into direct hidden instructions:

```text
Do not auto-commit code.
Always answer in Chinese.
This repo uses pytest.
```

The downstream agent should reason over evidence, time, scope, and conflicts.
NanoMem should not silently synthesize a canonical user profile.

## What To Store

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

NanoMem intentionally keeps the agent-facing surface small:

```text
capture
read
```

`flush` is a session/window control operation. It seals pending dialogue
buffers and makes extracted units searchable. Admin, backup, export, retention,
delete, reindex, and raw dialogue inspection belong to CLI or control-plane
surfaces, not to ordinary agent tools.

### HTTP

```text
GET  /v1/health
POST /v1/capture
POST /v1/flush
POST /v1/read
```

Capture without `session_id` is a complete dialogue and extracts immediately.
Capture with `session_id` appends raw messages to that session's open dialogue
window; call `/v1/flush` when a session pauses, exits, or should become
searchable before the token window fills. Because windows do not store memory
scope, flushing a pending window requires both `session_id` and extraction
`scope`.

CLI equivalent:

```bash
nanomem flush --config nanomem.json --user-id demo-user --session-id codex-session
```

The JSON request and response shapes are documented in
[docs/reports/request-response-examples.md](docs/reports/request-response-examples.md).

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

### MCP

Run the stdio MCP server:

```bash
nanomem-mcp --config nanomem.json
```

MCP exposes `nanomem_read` only. Writes go through hook capture, the SDK, or
the HTTP API, not through model-selected MCP tools. Control-plane actions such
as backup, export, retention, and reindex should also stay out of the MCP
surface.

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
```

Backup, export, and retention examples:

```bash
nanomem backup --config nanomem.json --output .nanomem/backups/backup.db
nanomem export --config nanomem.json --output .nanomem/exports/export.json
nanomem retention-preview --config nanomem.json --before 2026-01-01T00:00:00+00:00
nanomem log-retention-preview --config nanomem.json --before 2026-01-01T00:00:00+00:00
```

If the package is not installed, use module entry points from the repo root:

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

| Key | Values |
| --- | --- |
| `store.backend` | `sqlite` |
| `index.backend` | `lexical`, `dense`, `hybrid`, `lancedb` |
| `index.embedding.backend` | `hashing`, `openai_compatible` |
| `extraction.backend` | `heuristic`, `llm` |
| `read.default_recency_policy` | `recent`, `balanced`, `historical` |

The default local setup is dependency-light:

- SQLite is the fact store;
- `dense` is the default index backend;
- deterministic local hashing is the default embedding model;
- `heuristic` is the default extractor;
- `index.rebuild_on_startup = true` rebuilds derived indexes from SQLite.

Use environment variables for provider credentials. Do not put API keys in
config files committed to the repository.

### Optional LanceDB

Install the optional dependency:

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
nanomem-agent-hook spool --host codex
nanomem-agent-hook read --host codex
nanomem-agent-hook capture --host codex
nanomem-agent-hook spool --host claude-code
nanomem-agent-hook read --host claude-code
nanomem-agent-hook capture --host claude-code
```

The plugins are explicit opt-in integrations. They connect to a local HTTP
sidecar by default. For Codex, install project-level hooks first:

```bash
nanomem install-codex-hooks --project-dir .
```

Plugin-bundled Codex hooks remain an opt-in packaging path and should be
validated separately. On the checked local CLI, interactive Codex executed
project hooks after hook trust, while `codex exec` did not execute project,
user, or plugin-bundled hooks.

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

Detailed plugin docs:

- [docs/plugins/README.md](docs/plugins/README.md)
- [docs/plugins/codex.md](docs/plugins/codex.md)
- [docs/plugins/codex-installation.md](docs/plugins/codex-installation.md)
- [docs/plugins/claude-code.md](docs/plugins/claude-code.md)

## Project Layout

```text
src/nanomem/
  contracts.py        # core data contracts
  config.py           # JSON / simple YAML config loading
  factory.py          # config-driven construction
  service/            # capture/read orchestration
  store/              # SQLite persistence
  index/              # lexical, dense, hybrid, LanceDB adapters
  embeddings/         # hashing and OpenAI-compatible embeddings
  extraction/         # heuristic and LLM extractors
  ranking/            # relevance and recency ranking
  render/             # packed context rendering
  server/             # HTTP API and manager routes
  mcp/                # stdio MCP server
  sdk/                # Python HTTP clients
  cli/                # command-line administration
  control/            # stats, backup, export, retention, reindex
  maintenance/        # configured maintenance workflows
  adapters/           # host integration adapters
  manager/            # bundled manager assets
manager-ui/           # React/Vite manager source
docs/                 # product, architecture, manager, and plugin docs
tests/                # pytest regression tests
```

Architecture rule of thumb:

```text
server -> service -> store/index/extraction/ranking/render -> contracts
```

The service layer owns orchestration. Stores and indexes expose capabilities;
they should not decide capture/read behavior.

## Development

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
PYTHONPATH=src python -m pytest
```

Run a focused LanceDB integration test after installing the extra:

```bash
python -m pip install -e ".[dev,lancedb]"
PYTHONPATH=src python -m pytest tests/index/test_lancedb_integration.py
```

CI runs compile and pytest on Python 3.10, 3.11, and 3.12.

## Security And Data

NanoMem stores personal memory data.

- Do not commit `.nanomem/`, local databases, exports, backups, `.env`, or API keys.
- Bind the HTTP server to `127.0.0.1` for local use.
- Do not expose `/manager` or `/manager/api/*` to untrusted networks.
- Keep raw workspace files, logs, tool output, and multimodal assets outside NanoMem.
- Use backup/export/retention commands with temporary paths in tests.
- Enable hook debug payloads only temporarily; they may contain prompt or transcript metadata.

## Documentation Map

- [docs/system-design.md](docs/system-design.md): top-level product and architecture design.
- [docs/nanomem/README.md](docs/nanomem/README.md): modular design specs.
- [docs/nanomem-product-rfc.md](docs/nanomem-product-rfc.md): product boundary and memory semantics.
- [docs/agent-memory-positioning.md](docs/agent-memory-positioning.md): agent read/write guidance.
- [docs/architecture-overview.md](docs/architecture-overview.md): diagrams, runtime layout, and store/index split.
- [docs/index-backends.md](docs/index-backends.md): in-memory, LanceDB, and Postgres/pgvector strategy.
- [docs/nanomem-code-architecture.md](docs/nanomem-code-architecture.md): module-level implementation architecture.
- [docs/manager/README.md](docs/manager/README.md): web manager and control-plane design.
- [docs/reports/request-response-examples.md](docs/reports/request-response-examples.md): complete API examples.

## License

MIT. See package metadata in [pyproject.toml](pyproject.toml).
