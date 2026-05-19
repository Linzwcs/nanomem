from __future__ import annotations

from nanomem.contracts import (
    IndexHit,
    IndexSearchRequest,
    MemoryUnit,
)
from nanomem.embeddings.base import EmbeddingModel
from nanomem.embeddings.hashing import HashingEmbeddingModel
from nanomem.policies import namespace_matches
from nanomem.time import timestamp_in_range


class DenseMemoryUnitIndex:
    """Local vector index over personal fact units."""

    name = "dense_cosine_v1"
    default_scan_limit = 2_000

    def __init__(
        self,
        embedding_model: EmbeddingModel | None = None,
        *,
        scan_limit: int | None = None,
    ) -> None:
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.scan_limit = scan_limit or self.default_scan_limit
        self._documents: dict[str, MemoryUnit] = {}
        self._vectors: dict[str, tuple[float, ...]] = {}
        self._owner_index: dict[str, set[str]] = {}

    def clear(self) -> None:
        self._documents.clear()
        self._vectors.clear()
        self._scope_index.clear()

    def document_count(self) -> int:
        return len(self._documents)

    def upsert(self, units: tuple[MemoryUnit, ...]) -> None:
        texts = tuple(unit.text for unit in units)
        vectors = self.embedding_model.embed(texts) if texts else ()
        for unit, vector in zip(units, vectors):
            existing = self._documents.get(unit.unit_id)
            if existing is not None:
                self._remove_from_scope_index(existing)
            self._documents[unit.unit_id] = unit
            self._vectors[unit.unit_id] = vector
            self._add_to_scope_index(unit)

    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]:
        query_vector = self.embedding_model.embed((request.query,))[0]
        hits: list[IndexHit] = []
        scanned = 0
        for unit_id, unit in self._candidate_units(request):
            timestamp = unit.timestamp or unit.available_at
            scanned += 1
            if scanned > self.scan_limit:
                break
            if unit.scope.owner_id != request.owner_id:
                continue
            if not namespace_matches(unit.scope.namespace or "", request.namespaces):
                continue
            if not timestamp_in_range(timestamp, request.time_range):
                continue
            score = cosine_similarity(
                query_vector,
                self._vectors.get(unit_id, ()),
            )
            if score <= 0.0:
                continue
            hits.append(
                IndexHit(
                    unit_id=unit_id,
                    score=score,
                    retrieval_text=unit.text,
                    score_breakdown={
                        "dense": score,
                        "embedding_model": self.embedding_model.name,
                        "scanned_count": scanned,
                        "scan_limit": self.scan_limit,
                    },
                )
            )
        hits.sort(key=lambda hit: (-hit.score, hit.unit_id))
        if request.limit is not None:
            hits = hits[:request.limit]
        return tuple(hits)

    def delete(self, unit_ids: tuple[str, ...]) -> None:
        for unit_id in unit_ids:
            unit = self._documents.pop(unit_id, None)
            if unit is not None:
                self._remove_from_scope_index(unit)
            self._vectors.pop(unit_id, None)

    def _candidate_units(
        self,
        request: IndexSearchRequest,
    ) -> tuple[tuple[str, MemoryUnit], ...]:
        ids = self._owner_index.get(request.owner_id, set())
        units = tuple(
            (unit_id, self._documents[unit_id])
            for unit_id in ids
            if unit_id in self._documents
        )
        return tuple(
            sorted(
                units,
                key=lambda item: (
                    item[1].timestamp or item[1].available_at,
                    item[0],
                ),
                reverse=True,
            )
        )

    def _add_to_scope_index(self, unit: MemoryUnit) -> None:
        self._owner_index.setdefault(unit.scope.owner_id, set()).add(unit.unit_id)

    def _remove_from_scope_index(self, unit: MemoryUnit) -> None:
        ids = self._owner_index.get(unit.scope.owner_id)
        if ids is None:
            return
        ids.discard(unit.unit_id)
        if not ids:
            self._owner_index.pop(unit.scope.owner_id, None)


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    score = sum(a * b for a, b in zip(left, right))
    return max(score, 0.0)
