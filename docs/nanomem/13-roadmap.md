# Roadmap

Status: draft

This document defines the staged implementation plan for the clean NanoMem
design.

## Phase 0: Design Freeze

Goals:

- freeze product boundary and MemoryUnit style;
- freeze core contracts and service interfaces;
- keep session, project, agent, and host ids out of core scope;
- align README and modular docs.

Exit criteria:

- `00` through `13` specs are internally consistent;
- examples use required timestamps;
- no separate external-resource reference model remains in the first-version
  design.

## Phase 1: Core Contract Migration

Goals:

- update `contracts.py` to match `MemoryScope`, `CaptureDialogue`,
  `DialogueRecord`, `DialogueRef`, `MemoryUnit`, `CaptureRequest`, and
  `ReadRequest`;
- make time required in contracts;
- keep metadata as custom JSON only;
- preserve old code paths only behind explicit compatibility shims if needed.

Exit criteria:

- import/compile checks pass;
- focused unit tests cover contract serialization and validation;
- README examples match accepted request shapes.

## Phase 2: SQLite Store Stabilization

Goals:

- persist MemoryUnits, DialogueRecords, operation logs, and schema migrations;
- keep DialogueRecords out of normal read;
- implement retention/redaction state required by the store contract.

Exit criteria:

- store tests cover append, query, dialogue archive, operation logs, and redaction;
- index rebuild works from stored MemoryUnits.

## Phase 3: Capture And Extraction

Goals:

- enforce bounded `CaptureDialogue`;
- archive DialogueRecord before extraction;
- extract third-person, evidence-grounded MemoryUnits;
- return explicit skip reasons.

Exit criteria:

- tests cover user preference, correction, workspace-local skip, tool-output
  skip, multi-speaker attribution, replay behavior, and conflicting facts.

## Phase 4: Read, Ranking, And Render

Goals:

- require `query_time`;
- retrieve through index and load authoritative units from store;
- rank evidence by relevance, recency, namespace, type, and confidence;
- render under post-render token budget with mandatory timestamps.

Exit criteria:

- tests cover namespace defaults, time ranges, conflicts, budget packing, and
  structured `ranked_units`.

## Phase 5: Adapter Hardening

Goals:

- map HTTP, MCP, CLI, and SDK payloads onto the core contracts;
- keep admin/control-plane operations out of agent-facing tools;
- document integration examples for local agent harnesses.

Exit criteria:

- smoke tests cover HTTP/MCP capture and read;
- admin CLI covers backup, export, retention preview/apply, reindex, and
  integrity check.

## Phase 6: Index Extensions

Goals:

- keep lexical/dense/hybrid as baseline;
- add LanceDB adapter for local persistent ANN if needed;
- evaluate Postgres + pgvector only for managed multi-user deployments.

Exit criteria:

- LanceDB/pgvector adapters remain behind `MemoryUnitIndex`;
- service code has no backend-specific imports;
- indexes remain rebuildable from the authoritative store.
