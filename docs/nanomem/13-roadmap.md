# Roadmap

Status: active draft

This roadmap starts from the current verified implementation rather than the
original design-only plan. NanoMem already has an end-to-end local MVP:

```text
agent/dialogue -> capture -> DialogueRecord -> extraction -> MemoryUnit
  -> SQLite store -> dense index -> read -> rank -> render -> agent context
```

## Verified Baseline

Validation date: 2026-05-23.

Commands run:

```bash
python -m pytest
python -m pytest tests/product/test_local_memory_flow.py
```

Observed results:

```text
62 passed, 5 skipped
1 product-flow regression passed
```

The product-flow regression verifies the local developer-preview path:

- `capture` archives `DialogueRecord`s before extracting `MemoryUnit`s;
- SQLite persists units, dialogues, and operation logs across service restart;
- startup reindex rebuilds the derived dense index from SQLite;
- `read` retrieves namespace-scoped facts and renders timestamped context under
  a token budget;
- time range filters exclude ineligible memory evidence;
- Manager APIs expose stats, memory list/detail, source dialogue evidence,
  retrieval preview, reindex, and operation logs.

Agent adapter E2E also passed:

- `after_turn` writes dialogue and memory units;
- `read` retrieves relevant memory;
- renderer returns timestamped context under budget.

## Current Capability

Implemented:

- core contracts for `MemoryScope`, `CaptureDialogue`, `DialogueRecord`,
  `DialogueRef`, `MemoryUnit`, `CaptureRequest`, and `ReadRequest`;
- SQLite authoritative store for units, dialogues, operation logs, schema
  state, backup/export, and retention primitives;
- capture pipeline with dialogue archival before extraction;
- heuristic extractor with skip reasons for non-memory content;
- dense in-memory vector index with hashing embeddings;
- lexical fallback when the active index returns no hits;
- ranker and timestamped context renderer with post-render token budget;
- HTTP server, SDK client, MCP server, CLI, and local `AgentMemoryAdapter`;
- `nanomem.manager` local management UI with dashboard, memory list/detail,
  multi-turn evidence log, operation logs, retrieval lab, and system health.

Known limits:

- extraction quality is MVP-level unless an LLM extractor is configured;
- dense index is in-memory and is rebuilt from SQLite on startup by default;
- LanceDB has local persistent-index smoke coverage with hashing embeddings,
  but still needs runtime quality checks with real embedding providers;
- render format is simple and not yet optimized for maximum facts per budget;
- control-plane maintenance workflows are partly CLI/service-level and not fully exposed
  in Manager;
- operation log payloads still need stricter minimization before sensitive use.

## Developer Preview Gate

NanoMem can be treated as a local alpha product when the product-flow regression
passes. Developer preview should additionally require:

- frozen HTTP/SDK/MCP contract examples for `capture`, `read`, and manager
  retrieval preview;
- one recommended local configuration using SQLite plus dense or LanceDB index;
- explicit setup docs for sidecar usage without system-wide installation;
- browser-verified Manager UI for memory list, source evidence, retrieval lab,
  operation logs, and index health;
- documented limitations for heuristic extraction, hashing embeddings, and
  operation-log payload sensitivity.

## Milestone 1: Contract Freeze

Goal: make the current MVP contracts stable enough for adapter and backend work.

Work:

- review every public dataclass field and serialization helper;
- freeze `MemoryUnit`, `DialogueRecord`, `DialogueRef`, `CaptureRequest`, and
  `ReadRequest`;
- document compatibility rules for `owner_id`, namespace lists, timestamps, and
  metadata;
- add regression tests for malformed payloads and backward-compatible aliases.

Exit criteria:

- contract docs match code exactly;
- HTTP, SDK, MCP, CLI, and manager tests all pass;
- examples in README and `docs/reports/request-response-examples.md` use the
  frozen shapes.

## Milestone 2: LLM Extraction

Goal: replace heuristic-only capture with production-quality fact extraction.

Current baseline:

- OpenAI-compatible LLM extractor supports injectable completion clients for
  deterministic tests;
- extraction filters hidden/tool/non-visible messages before model calls;
- role-aware internal chunks preserve original message indexes and split across
  non-extractable gaps;
- LLM prompt/schema requires third-person evidence phrasing; heuristic remains
  a simple smoke-test extractor;
- strict payload validation covers `message_range`, `memory_type`,
  non-extractable evidence ranges, and out-of-chunk ranges;
- deterministic fake-LLM fixtures cover preference, correction, user event,
  agent interaction, workspace skip, tool-log skip, and multi-turn attribution;
- extractor-agnostic eval harness reports expected unit/skip matches before
  real provider quality runs;
- provider errors, missing API keys, and invalid strict payloads can fall back
  to the heuristic extractor.

Work:

- improve prompt fixtures against real model responses;
- add offline eval data for extraction precision and recall;
- tune chunk sizing defaults after measuring latency and quality.

Exit criteria:

- tests cover preference, correction, user event, agent behavior, workspace
  skip, tool-log skip, and multi-turn attribution;
- extraction fixtures are deterministic in test mode;
- Manager evidence clearly shows the source range inside the original dialogue.

## Milestone 3: Persistent Vector Index

Goal: keep SQLite as authoritative store while making retrieval practical for
larger local stores.

Current baseline:

- `lancedb` backend is available behind `MemoryUnitIndex`;
- the adapter duplicates only search-time fields and remains rebuildable from
  SQLite;
- `tests/index/test_lancedb_integration.py` verifies SQLite capture,
  LanceDB persistence, service restart, and read-pipeline retrieval when the
  optional dependency is installed;
- default installs stay lightweight because LanceDB is optional.

Work:

- keep dense in-memory and lexical indexes as test/dev baselines;
- add index metadata, freshness checks, and safe rebuild behavior;
- ensure redacted units are excluded from index rebuilds.

Exit criteria:

- service code has no backend-specific imports;
- reindex can rebuild the selected backend from SQLite;
- retrieval latency is bounded without full in-memory similarity scans;
- tests cover restart persistence and index lag reporting.

## Milestone 4: Render Algorithm

Goal: maximize useful facts under the same post-render token budget.

Work:

- separate candidate retrieval, ranking, packing, and text formatting;
- make render policy deterministic and inspectable;
- prefer high-value short facts when budget is tight;
- surface diagnostics when ranked hits exist but no unit fits the budget;
- keep timestamps mandatory in rendered output.

Exit criteria:

- tests cover small, medium, and large budgets;
- returned context includes the maximum feasible number of useful units for a
  fixed ranked set;
- Retrieval Lab shows ranked count, rendered count, token count, and skipped
  due-to-budget count.

## Milestone 5: Agent Integration

Goal: make NanoMem easy to attach to local agent harnesses without becoming a
general workspace-memory system.

Work:

- define the sidecar pattern: `before_turn -> read`, `after_turn -> capture`;
- document Codex, Claude Code, OpenClaw, and generic local-agent usage;
- keep manager/control-plane endpoints out of agent-facing tools;
- add request/response examples for HTTP and MCP;
- add smoke tests for remote HTTP-backed `AgentMemoryAdapter`.

Exit criteria:

- a local agent can read memories before a turn and capture visible dialogue
  after a turn;
- examples do not store raw files, tool logs, or multimodal assets;
- namespace behavior is clear: default read searches all namespaces unless
  restricted by host policy.

## Milestone 6: Manager Operations

Goal: make the local management UI a reliable operator surface.

Work:

- introduce a React/Vite source tree while keeping `/manager` served by the
  existing Python server;
- add pagination and URL-persistent filters;
- move evidence resolution out of `server/manager.py` into a control service module;
- expose backup, export, integrity check, retention preview, and reindex history;
- add redaction preview and source dialogue reveal audit;
- improve operation log minimization.

Exit criteria:

- Manager handles larger stores without loading every record;
- destructive actions use preview/apply flows;
- no login/auth work is required for this local-first milestone;
- raw dialogue remains audit-only and is not indexed.

## Deferred

These are intentionally out of the near-term roadmap:

- login/authentication and hosted multi-user role systems;
- all-in-one document, code, media, and memory storage;
- direct indexing of raw dialogue or multimodal resources;
- Postgres/pgvector until managed multi-user deployment is needed;
- automatic memory editing without explicit evidence and audit trail.
