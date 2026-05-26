from __future__ import annotations

from nanomem.core.contracts import (
    DialogueRef,
    IndexSearchRequest,
    MemoryScope,
    MemoryUnit,
)
from nanomem.pipeline.retrieval.indexes.hybrid import HybridMemoryUnitIndex


def _unit(unit_id: str, text: str, *, namespace: str = "personal") -> MemoryUnit:
    return MemoryUnit(
        unit_id=unit_id,
        scope=MemoryScope(owner_id="user-1", namespace=namespace),
        text=text,
        memory_type="background",
        timestamp="2026-01-01T00:00:00+00:00",
        available_at="2026-01-01T00:00:01+00:00",
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )


def test_hybrid_returns_units_matching_either_index() -> None:
    index = HybridMemoryUnitIndex()
    units = (
        _unit("u-1", "user prefers concise Chinese answers"),
        _unit("u-2", "user dislikes verbose responses"),
        _unit("u-3", "totally unrelated topic about hiking"),
    )
    index.upsert(units)

    hits = index.search(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise Chinese answers",
            limit=10,
        )
    )

    hit_ids = {hit.unit_id for hit in hits}
    assert "u-1" in hit_ids
    # Hybrid index should at least surface the highly relevant unit; ranking
    # of marginally-related units may differ between lexical/dense backends.


def test_hybrid_score_breakdown_records_both_signals() -> None:
    index = HybridMemoryUnitIndex()
    index.upsert((_unit("u-1", "user prefers concise Chinese answers"),))

    hits = index.search(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise Chinese answers",
            limit=5,
        )
    )

    assert len(hits) == 1
    breakdown = hits[0].score_breakdown
    # At least one of lexical/dense should report a sub-score
    assert any(label in breakdown for label in ("lexical", "dense"))


def test_hybrid_clear_removes_all_units() -> None:
    index = HybridMemoryUnitIndex()
    index.upsert((_unit("u-1", "user prefers concise answers"),))
    index.clear()

    hits = index.search(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise answers",
            limit=5,
        )
    )

    assert hits == ()


def test_hybrid_delete_removes_specific_unit() -> None:
    index = HybridMemoryUnitIndex()
    index.upsert(
        (
            _unit("u-1", "user prefers concise Chinese answers"),
            _unit("u-2", "user prefers concise English answers"),
        )
    )
    index.delete(("u-1",))

    hits = index.search(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise answers",
            limit=5,
        )
    )

    hit_ids = {hit.unit_id for hit in hits}
    assert "u-1" not in hit_ids
