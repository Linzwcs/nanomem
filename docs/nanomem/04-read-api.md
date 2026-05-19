# Read API

Status: draft

This document defines the intended read API. It is a design target and may be
ahead of the current implementation.

## 1. Purpose

`read` retrieves relevant personal MemoryUnits and renders them as evidence for
the agent prompt.

Read does not return a canonical user profile. It returns timestamped evidence
so the downstream agent can reason over recency, scope, and conflicts.

## 2. Request Shape

```python
ReadRequest:
  owner_id: str
  namespaces: tuple[str, ...] | None
  query: str | dict
  query_time: str
  time_range: TimeRange | None
  recency_policy: "recent" | "balanced" | "historical"
  max_units: int | None
  context_budget_tokens: int | None
  metadata: dict
```

`owner_id` is required.

`namespaces` controls which stable memory categories are searched.

```python
TimeRange:
  start: str | None
  end: str | None
```

## 3. Core Invariants

Read has these first-version invariants:

- `owner_id` and `query_time` are required.
- All request times use ISO 8601 with timezone.
- `metadata` is caller-defined JSON and must not change core scope or time
  semantics.
- Read searches MemoryUnits, not raw DialogueRecords.
- The store is authoritative; indexes only return candidates.
- `ReadResult.ranked_units` may contain full structured metadata and
  `dialogue_refs`.
- `PackedContext.text` must include a timestamp for every rendered MemoryUnit.
- Read returns evidence, not direct instructions and not a canonical profile.
- `context_budget_tokens` applies to final rendered text, not pre-render
  candidate text.

## 4. Namespace Semantics

Read defaults to all allowed namespaces for the owner.

Rules:

- `namespaces=None`: search all configured `allowed_namespaces`;
- `namespaces=("work", "research")`: search exactly those namespaces;
- every requested namespace must be in `allowed_namespaces`;
- wildcard namespace strings are not part of the first design;
- extractors do not decide read namespaces.

Reasoning:

Users usually expect their personal memory to be found even if they do not
remember whether a fact was stored under `personal`, `work`, or `research`.
Namespace filters remain available for callers that need a narrower context.

## 5. Query And Time

`query` may be plain text or a structured object. Structured queries should be
converted into retrieval text without losing the original metadata.

`time_range` explicitly bounds retrieval. If it is omitted, NanoMem should not
hard-filter old memories by default. Recency policy and `query_time` influence
ranking, while explicit `time_range` is the mechanism for strict time bounds.

`query_time` is the read-time anchor for recency scoring. If an API surface
wants to omit it for convenience, the service must resolve it to a concrete
timestamp before policy and ranking run.

`time_range.start` and `time_range.end` are inclusive bounds over
`MemoryUnit.timestamp`. `None` means unbounded on that side.

## 6. Pipeline

```text
ReadRequest
  -> validate owner and namespaces
  -> resolve namespace set
  -> resolve query text
  -> resolve explicit time filter, if provided
  -> retrieve candidate MemoryUnits
  -> load authoritative units from store
  -> rank evidence
  -> render under post-render token budget
  -> record operation log
```

## 7. Response Shape

```python
ReadResult:
  request: ReadRequest
  ranked_units: tuple[RankedMemoryUnit, ...]
  context: PackedContext
  stats: dict
  trace_ref: str | None
```

```python
RankedMemoryUnit:
  unit: MemoryUnit
  rank: int
  score: float
  retrieval_text: str
  score_breakdown: dict
```

```python
PackedContext:
  text: str
  token_count: int
  unit_count: int
```

## 8. Rendering Requirements

Rendering should:

- preserve third-person MemoryUnit text;
- include the MemoryUnit timestamp for every rendered item;
- allow all non-time labels, such as dialogue ref, namespace, confidence, tags,
  or project hints, to be configured by the host renderer;
- avoid turning memories into direct instructions;
- keep conflicting facts visible when relevant;
- maximize useful fact coverage under the post-render token budget.

The structured `ReadResult.ranked_units` may include full metadata and
`dialogue_refs`. `PackedContext.text` has a stricter rule: time is mandatory,
while other bracket fields are optional rendering metadata.

Example:

```text
Relevant personal memory:
- [2026-01-05] The user said they prefer concise Chinese answers.
- [2026-05-19, namespace=work] The user decided NanoMem should not store workspace documents.
```
