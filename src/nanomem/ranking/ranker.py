from __future__ import annotations

from nanomem.contracts import (
    IndexHit,
    MemoryUnit,
    RankedMemoryUnit,
)
from nanomem.time import recency_score


class MemoryUnitRanker:
    name = "relevance_recency_v1"

    def rank(
        self,
        units: tuple[MemoryUnit, ...],
        *,
        hits: dict[str, IndexHit],
        query_time: str | None,
        recency_policy: str,
        limit: int | None,
    ) -> tuple[RankedMemoryUnit, ...]:
        ranked: list[RankedMemoryUnit] = []
        for unit in units:
            hit = hits.get(unit.unit_id)
            relevance = hit.score if hit else 0.0
            if relevance <= 0.0:
                continue
            recency = recency_score(
                unit.timestamp or unit.available_at,
                query_time=query_time,
            )
            score = _combine_score(
                relevance=relevance,
                recency=recency,
                recency_policy=recency_policy,
            )
            ranked.append(
                RankedMemoryUnit(
                    unit=unit,
                    rank=0,
                    score=score,
                    retrieval_text=hit.retrieval_text if hit else unit.text,
                    score_breakdown={
                        "relevance": relevance,
                        "recency": recency,
                        "recency_policy": recency_policy,
                        **(hit.score_breakdown if hit else {}),
                    },
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.score,
                -(recency_score(
                    item.unit.timestamp or item.unit.available_at,
                    query_time=query_time,
                )),
                item.unit.unit_id,
            )
        )
        if limit is not None:
            ranked = ranked[:limit]
        return tuple(
            RankedMemoryUnit(
                unit=item.unit,
                rank=rank,
                score=item.score,
                retrieval_text=item.retrieval_text,
                score_breakdown=item.score_breakdown,
            )
            for rank, item in enumerate(ranked, start=1)
        )


def _combine_score(
    *,
    relevance: float,
    recency: float,
    recency_policy: str,
) -> float:
    if recency_policy == "historical":
        return relevance
    if recency_policy == "balanced":
        return 0.75 * relevance + 0.25 * recency
    return 0.65 * relevance + 0.35 * recency
