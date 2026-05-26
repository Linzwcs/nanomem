from __future__ import annotations

import json
from typing import Any

from nanomem.core.contracts import (
    IndexHit,
    IndexSearchRequest,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    RankedMemoryUnit,
    ReadRequest,
    ReadResult,
)
from nanomem.core.errors import ContractError
from nanomem.core.ids import new_id
from nanomem.pipeline.retrieval.indexes.base import MemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.lexical import tokenize
from nanomem.pipeline.retrieval.ranking.relevance_recency import MemoryUnitRanker
from nanomem.pipeline.utilization.evidence_context import (
    EvidenceContextRenderer,
    estimate_tokens,
    render_line_for_diagnostics,
)
from nanomem.pipeline.storage.base import MemoryStore
from nanomem.core.time import now_utc_iso


class ReadPipeline:
    def __init__(
        self,
        *,
        store: MemoryStore,
        index: MemoryUnitIndex,
        ranker: MemoryUnitRanker,
        renderer: EvidenceContextRenderer,
        default_recency_policy: str,
        default_max_units: int,
    ) -> None:
        self.store = store
        self.index = index
        self.ranker = ranker
        self.renderer = renderer
        self.default_recency_policy = default_recency_policy
        self.default_max_units = default_max_units

    def run(self, request: ReadRequest) -> ReadResult:
        _validate_read_request(request)
        query = _query_text(request.query)
        recency_policy = request.recency_policy or self.default_recency_policy
        _validate_recency_policy(recency_policy)
        max_units = (
            request.max_units
            if request.max_units is not None
            else self.default_max_units
        )
        candidate_limit = max(max_units * 5, max_units)
        hits = self.index.search(
            IndexSearchRequest(
                owner_id=request.owner_id,
                namespaces=request.namespaces,
                query=query,
                time_range=request.time_range,
                limit=candidate_limit,
            )
        )
        if not hits:
            hits = _scan_store_for_hits(
                self.store.query_units(
                    MemoryUnitSelector(
                        owner_id=request.owner_id,
                        namespaces=request.namespaces,
                        time_range=request.time_range,
                        limit=candidate_limit,
                    )
                ),
                query=query,
                limit=candidate_limit,
            )
        hit_by_id = {hit.unit_id: hit for hit in hits}
        units = self.store.get_units(tuple(hit.unit_id for hit in hits))
        ranked = self.ranker.rank(
            units,
            hits=hit_by_id,
            query_time=request.query_time,
            recency_policy=recency_policy,
            limit=max_units,
        )
        context = self.renderer.render(
            ranked,
            budget_tokens=request.context_budget_tokens,
        )
        render_diagnostics = _render_diagnostics(
            ranked,
            rendered_text=context.text,
            budget_tokens=request.context_budget_tokens,
        )
        result = ReadResult(
            request=request,
            ranked_units=ranked,
            context=context,
            stats={
                "query": query,
                "time_range_filter": {
                    "start": request.time_range.start if request.time_range else None,
                    "end": request.time_range.end if request.time_range else None,
                },
                "candidate_count": len(hits),
                "ranked_count": len(ranked),
                "returned_unit_count": context.unit_count,
                "rendered_unit_ids": render_diagnostics["rendered_unit_ids"],
                "skipped_unit_ids": render_diagnostics["skipped_unit_ids"],
                "skipped_due_to_budget_count": render_diagnostics[
                    "skipped_due_to_budget_count"
                ],
                "context_budget_tokens": request.context_budget_tokens,
                "context_tokens": context.token_count,
                "ranked_token_estimates": render_diagnostics[
                    "ranked_token_estimates"
                ],
                "index_backend": getattr(self.index, "name", type(self.index).__name__),
                "recency_policy": recency_policy,
                "ranking_policy": self.ranker.name,
                "render_policy": self.renderer.name,
            },
        )
        self._record_read_log(request, result, ranked, query, recency_policy)
        return result

    def _record_read_log(
        self,
        request: ReadRequest,
        result: ReadResult,
        ranked: tuple[RankedMemoryUnit, ...],
        query: str,
        recency_policy: str,
    ) -> None:
        created_at = now_utc_iso()
        self.store.append_operation_log(
            OperationLogEntry(
                log_id=new_id("oplog"),
                operation_type="read",
                created_at=created_at,
                scope=None,
                status="ok",
                summary={
                    "owner_id": request.owner_id,
                    "candidate_count": result.stats["candidate_count"],
                    "ranked_count": result.stats["ranked_count"],
                    "returned_unit_count": result.stats["returned_unit_count"],
                    "context_tokens": result.stats["context_tokens"],
                },
                payload={
                    "query": query,
                    "query_time": request.query_time,
                    "namespaces": request.namespaces,
                    "recency_policy": recency_policy,
                    "ranked_units": [_ranked_unit_log_payload(item) for item in ranked],
                    "response_text": result.context.text,
                    "stats": result.stats,
                },
            )
        )


def _validate_read_request(request: ReadRequest) -> None:
    if not request.owner_id:
        raise ContractError("ReadRequest.owner_id is required")
    if not request.query_time:
        raise ContractError("ReadRequest.query_time is required")


def _validate_recency_policy(value: str) -> None:
    if value not in {"recent", "balanced", "historical"}:
        raise ContractError(f"Unsupported recency_policy: {value}")


def _query_text(query: str | dict[str, Any]) -> str:
    if isinstance(query, str):
        return query
    value = query.get("question") or query.get("query") or query.get("text")
    if value is not None:
        return str(value)
    return json.dumps(query, ensure_ascii=False, sort_keys=True)


def _scan_store_for_hits(
    units: tuple[MemoryUnit, ...],
    *,
    query: str,
    limit: int,
) -> tuple[IndexHit, ...]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return ()
    hits: list[IndexHit] = []
    for unit in units:
        unit_tokens = tokenize(unit.text)
        overlap = query_tokens & unit_tokens
        if not overlap:
            continue
        score = len(overlap) / max(len(query_tokens), 1)
        hits.append(
            IndexHit(
                unit_id=unit.unit_id,
                score=score,
                retrieval_text=unit.text,
                score_breakdown={
                    "fallback": "store_scan",
                    "overlap": sorted(overlap),
                    "query_token_count": len(query_tokens),
                    "document_token_count": len(unit_tokens),
                },
            )
        )
    hits.sort(key=lambda hit: (-hit.score, hit.unit_id))
    return tuple(hits[:limit])


def _ranked_unit_log_payload(item: RankedMemoryUnit) -> dict[str, object]:
    return {
        "rank": item.rank,
        "unit_id": item.unit.unit_id,
        "score": item.score,
        "text": item.unit.text,
        "timestamp": item.unit.timestamp,
        "available_at": item.unit.available_at,
        "dialogue_refs": [
            {
                "dialogue_id": ref.dialogue_id,
                "message_range": ref.message_range,
            }
            for ref in item.unit.dialogue_refs
        ],
        "score_breakdown": item.score_breakdown,
    }


def _render_diagnostics(
    ranked: tuple[RankedMemoryUnit, ...],
    *,
    rendered_text: str,
    budget_tokens: int | None,
) -> dict[str, object]:
    del rendered_text
    lines = ["Relevant memory units:"]
    rendered_unit_ids: list[str] = []
    skipped_unit_ids: list[str] = []
    for index, item in enumerate(ranked):
        line = render_line_for_diagnostics(item)
        candidate = "\n".join([*lines, line])
        if budget_tokens is not None and estimate_tokens(candidate) > budget_tokens:
            skipped_unit_ids.append(item.unit.unit_id)
            if rendered_unit_ids:
                skipped_unit_ids.extend(
                    later.unit.unit_id
                    for later in ranked[index + 1:]
                )
                break
            continue
        lines.append(line)
        rendered_unit_ids.append(item.unit.unit_id)
    return {
        "rendered_unit_ids": tuple(rendered_unit_ids),
        "skipped_unit_ids": tuple(skipped_unit_ids),
        "skipped_due_to_budget_count": len(skipped_unit_ids)
        if budget_tokens is not None
        else 0,
        "ranked_token_estimates": [
            {
                "unit_id": item.unit.unit_id,
                "render_line_tokens": estimate_tokens(
                    render_line_for_diagnostics(item),
                ),
            }
            for item in ranked
        ],
    }
