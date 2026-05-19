# Retrieval, Ranking, And Render

Status: draft

This document defines how NanoMem reads stored MemoryUnits and turns them into
prompt-ready evidence.

## 1. Purpose

Read optimizes for useful personal evidence under a final prompt budget. It does
not return raw dialogue, raw chunks, or a canonical user profile.

The key goal is post-render fact coverage:

```text
under the same rendered token budget, preserve more relevant MemoryUnits
```

## 2. Candidate Retrieval

Candidate retrieval is a derived index operation.

```text
ReadRequest
  -> validate owner, namespaces, query_time
  -> resolve namespace set
  -> resolve explicit time filter, if provided
  -> convert query to retrieval text
  -> ask MemoryUnitIndex for candidate ids
  -> load authoritative MemoryUnits from store
```

Indexes must filter by owner and namespace when possible. They should apply an
explicit `time_range` when one is provided. If an index cannot enforce a filter,
the store load step must enforce it.

The index is never authoritative. It may store vectors, tokens, and duplicated
core fields for speed, but MemoryUnit content comes from the store. Arbitrary
metadata is not filterable unless selected keys are explicitly configured and
copied into the index.

## 3. Backend Expectations

First-version backends:

- `dense`: default bounded embedding retrieval after owner/namespace filtering;
- `lexical`: deterministic local token fallback and debugging baseline;
- `hybrid`: lexical and dense score merge.

Future ANN backends:

- LanceDB for local persistent vector search;
- Postgres + pgvector for managed deployments.

NanoMem core should not implement ANN algorithms. ANN belongs behind
`MemoryUnitIndex`.

## 4. Ranking

Ranking orders evidence, not truth.

Recommended ranking signals:

- query relevance;
- recency relative to `query_time`;
- namespace match;
- time-range match;
- memory type;
- confidence;
- metadata hints supplied by the host;
- conflict usefulness when older and newer facts are both relevant.

Ranking must not discard conflicting facts only because a newer fact exists.
When a conflict is relevant, both facts may be valuable if the renderer can fit
them.

## 5. Render Budget

`context_budget_tokens` is a post-render budget. The renderer must measure or
estimate the final text it returns, including timestamps, labels, bullets, and
section headers.

Do not optimize on pre-render candidate size. A concise rendered fact can be
more useful than a large raw chunk with low fact density.

## 6. Render Format

Rendered MemoryUnits must include time. Other labels are configurable.

Minimal format:

```text
Relevant personal memory:
- [2026-01-05] The user said they prefer concise Chinese answers.
```

Host-configured labels:

```text
Relevant personal memory:
- [2026-01-05, namespace=work] The user prefers design discussion before implementation.
- [2026-05-19, confidence=0.82] The user decided NanoMem should not store raw workspace documents.
```

The renderer may include dialogue refs, namespace, confidence, tags, project
hints, or memory type, but time is the only mandatory bracket field.

## 7. Render Rules

Rendering should:

- preserve third-person MemoryUnit text;
- include every rendered unit timestamp;
- avoid imperative phrasing that turns memory into a direct command;
- keep conflicts visible when relevant and budget allows;
- prefer compact one-line facts over verbose explanations;
- avoid raw DialogueRecord content;
- avoid raw metadata dumps;
- maximize relevant fact count under the final token budget.

Rendering may drop optional labels to fit more facts, but it must not drop the
timestamp or alter MemoryUnit text in a way that changes meaning.

## 8. Structured Results

`ReadResult.ranked_units` can expose structured evidence to trusted host code:

```python
RankedMemoryUnit:
  unit: MemoryUnit
  rank: int
  score: float
  retrieval_text: str
  score_breakdown: dict
```

This structured result may include `dialogue_refs` and metadata. Agent-facing
prompt text should still be the compact `PackedContext.text`.

## 9. Evaluation

Evaluate read quality after rendering, not only at candidate retrieval.

Recommended metrics:

- relevant MemoryUnits rendered under a fixed budget;
- timestamp preservation rate;
- conflict preservation when conflict is relevant;
- skip rate for workspace-local or non-personal facts;
- latency by backend and corpus size;
- score trace usefulness for debugging.
