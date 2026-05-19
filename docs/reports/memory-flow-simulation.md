# Memory Flow Simulation Report

Status: draft

Date: 2026-05-19

This report records an end-to-end local simulation of NanoMem's current memory
unit lifecycle: capture, extraction, SQLite persistence, dense index rebuild,
read retrieval, rendering, and operation logging.

Concrete JSON request/response examples for the same API surface are in
`docs/reports/request-response-examples.md`.

## 1. Environment

- Database path: `.nanomem/simulations/memory-flow/memory_flow.db`
- Store backend: SQLite schema version 3
- Index backend: `dense_cosine_v1`
- Embedding backend: local deterministic hashing embedding
- Extractor: `heuristic_v1`

The generated database is local test data under `.nanomem/` and is ignored by
Git.

## 2. Capture Simulation

Four `CaptureRequest` inputs were executed for owner `user-sim`.

| Scenario | Namespace | Input Messages | Units | Skips |
| --- | --- | ---: | ---: | ---: |
| preference | `personal` | 1 | 2 | 0 |
| namespace-specific design preference | `work` | 1 | 1 | 0 |
| workspace/tool-log skip | `personal` | 3 | 1 | 2 |
| correction | `personal` | 1 | 1 | 0 |

Observed generated units:

- `I prefer concise Chinese answers.`
- `Please remember that I usually want architecture first, then code.`
- `I prefer fact-level memory units when discussing NanoMem design.`
- `Please remember that I do not want raw tool logs stored as long-term personal memory.`
- `Correction: I now prefer concise plans unless I explicitly ask for detail.`

The workspace/tool-log case behaved as intended:

- README-style workspace fact was skipped with `workspace_fact`;
- tool output was skipped with `invalid_role`;
- durable personal correction was retained as a `MemoryUnit`.

## 3. Direct Store Append

One manual `MemoryUnit` was inserted directly into SQLite:

```text
manual_unit_sim_001
namespace=manual
text=The user wants manually inserted memory units to be retrievable after index rebuild.
```

Before rebuilding the dense index, the index had 5 documents from service-level
captures. After querying all stored units and calling `index.upsert(...)`, the
index contained 6 documents. This confirms the intended separation:

- `CapturePipeline` writes both store and active index;
- direct store writes require explicit index upsert or rebuild for dense search;
- SQLite remains the source of truth.

## 4. Read Simulation

After rebuilding the dense index from SQLite, read requests produced:

| Query | Namespace Filter | Hits | Context Units | Notes |
| --- | --- | ---: | ---: | --- |
| `answer style architecture first concise plans` | all | 3 | 3 | correction ranked first |
| `NanoMem fact-level memory units` | `work` | 1 | 1 | namespace filter worked |
| `manually inserted retrievable index rebuild` | `manual` | 1 | 1 | manual unit retrievable after rebuild |
| `answer style` | other owner | 0 | 0 | owner isolation worked |
| `concise plans architecture` with `start=2026-05-04` | all | 1 | 1 | time range hard-filtered old units |
| small context budget, 32 tokens | all | 3 | 0 | hits found, but no rendered unit fit budget |

All read paths used `dense_cosine_v1`.

## 5. Store State

Final SQLite stats:

```text
unit_count=6
dialogue_count=4
operation_log_count=12
owner_count=1
namespace_count=3
```

Top owner/namespace counts:

- `user-sim / personal`: 4 units
- `user-sim / work`: 1 unit
- `user-sim / manual`: 1 unit

Dialogue evidence links were also verified: sampled units point back to existing
`DialogueRecord` rows with the expected `message_range`.

## 6. Issue Found And Fixed

During repeated read simulation, the old operation log id generation collided
when the same query was executed more than once within the same second.

Fix applied:

- added `new_id(prefix)` in `src/nanomem/ids.py`;
- changed capture/read operation logs to use runtime-unique log ids;
- added a regression test for repeated reads with the same query.

This keeps stable ids for durable domain records such as `MemoryUnit` and
`DialogueRecord`, while making operation logs append-only and collision-safe.

## 7. Observations

- The current core pipeline is functional for capture -> extract -> store ->
  dense index -> read -> render.
- Namespace and owner isolation work in the simulated cases.
- `DialogueRecord` is correctly archived but does not participate in normal read
  retrieval.
- Direct SQLite unit insertion is useful for tests, but production code should
  prefer service-level capture or a store+index maintenance helper.
- Tiny render budgets can produce ranked hits but zero rendered context units.
  This is correct under strict budget enforcement, but the renderer should later
  expose clearer diagnostics for "hits found but nothing fit".

## 8. Recommended Next Steps

1. Add an explicit `reindex` helper at the service/factory layer for reopening a
   SQLite store and rebuilding the active dense index.
2. Add tests for render budget behavior, especially small budgets and
   "maximize fact count under budget".
3. Add tests for workspace skip, tool-role skip, correction ranking, and
   DialogueRef integrity as permanent regression cases.
4. Decide whether direct manual unit insertion should be a first-class admin API
   or remain a low-level store operation.
