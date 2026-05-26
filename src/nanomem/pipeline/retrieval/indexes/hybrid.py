from __future__ import annotations

from nanomem.core.contracts import IndexHit, IndexSearchRequest, MemoryUnit
from nanomem.pipeline.retrieval.indexes.base import MemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.lexical import LexicalMemoryUnitIndex


class HybridMemoryUnitIndex:
    name = "hybrid_lexical_dense_v1"

    def __init__(
        self,
        *,
        lexical: MemoryUnitIndex | None = None,
        dense: MemoryUnitIndex | None = None,
        lexical_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> None:
        self.lexical = lexical or LexicalMemoryUnitIndex()
        self.dense = dense or DenseMemoryUnitIndex()
        self.lexical_weight = lexical_weight
        self.dense_weight = dense_weight

    def clear(self) -> None:
        self.lexical.clear()
        self.dense.clear()

    def document_count(self) -> int:
        lexical_count = _document_count(self.lexical)
        dense_count = _document_count(self.dense)
        return max(lexical_count, dense_count)

    def upsert(self, units: tuple[MemoryUnit, ...]) -> None:
        self.lexical.upsert(units)
        self.dense.upsert(units)

    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]:
        merged: dict[str, IndexHit] = {}
        for hit in self.lexical.search(request):
            merged[hit.unit_id] = _merge_hit(
                merged.get(hit.unit_id),
                hit,
                label="lexical",
                weight=self.lexical_weight,
            )
        for hit in self.dense.search(request):
            merged[hit.unit_id] = _merge_hit(
                merged.get(hit.unit_id),
                hit,
                label="dense",
                weight=self.dense_weight,
            )
        hits = sorted(merged.values(), key=lambda hit: (-hit.score, hit.unit_id))
        if request.limit is not None:
            hits = hits[:request.limit]
        return tuple(hits)

    def delete(self, unit_ids: tuple[str, ...]) -> None:
        self.lexical.delete(unit_ids)
        self.dense.delete(unit_ids)


def _merge_hit(
    existing: IndexHit | None,
    hit: IndexHit,
    *,
    label: str,
    weight: float,
) -> IndexHit:
    if existing is None:
        return IndexHit(
            unit_id=hit.unit_id,
            score=hit.score * weight,
            retrieval_text=hit.retrieval_text,
            score_breakdown={
                label: hit.score,
                f"{label}_breakdown": hit.score_breakdown,
            },
        )
    return IndexHit(
        unit_id=existing.unit_id,
        score=existing.score + hit.score * weight,
        retrieval_text=existing.retrieval_text,
        score_breakdown={
            **existing.score_breakdown,
            label: hit.score,
            f"{label}_breakdown": hit.score_breakdown,
        },
    )


def _document_count(index: MemoryUnitIndex) -> int:
    if hasattr(index, "document_count"):
        return int(index.document_count())  # type: ignore[attr-defined]
    return 0
