from __future__ import annotations

from nanomem.core.contracts import (
    DialogueRef,
    IndexHit,
    MemoryScope,
    MemoryUnit,
)
from nanomem.ranking.ranker import MemoryUnitRanker


def _unit(unit_id: str, text: str, timestamp: str) -> MemoryUnit:
    return MemoryUnit(
        unit_id=unit_id,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        text=text,
        memory_type="background",
        timestamp=timestamp,
        available_at=timestamp,
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )


def _hit(unit_id: str, score: float, retrieval_text: str = "") -> IndexHit:
    return IndexHit(
        unit_id=unit_id,
        score=score,
        retrieval_text=retrieval_text or unit_id,
    )


def test_rank_filters_units_with_zero_relevance() -> None:
    ranker = MemoryUnitRanker()
    units = (
        _unit("u-1", "fact A", "2026-01-01T00:00:00+00:00"),
        _unit("u-2", "fact B", "2026-01-01T00:00:00+00:00"),
    )
    hits = {"u-1": _hit("u-1", 0.8)}

    ranked = ranker.rank(
        units,
        hits=hits,
        query_time="2026-01-02T00:00:00+00:00",
        recency_policy="balanced",
        limit=None,
    )

    assert len(ranked) == 1
    assert ranked[0].unit.unit_id == "u-1"


def test_rank_orders_by_combined_score() -> None:
    ranker = MemoryUnitRanker()
    units = (
        _unit("u-1", "older but more relevant", "2025-01-01T00:00:00+00:00"),
        _unit("u-2", "recent and relevant", "2026-01-01T00:00:00+00:00"),
    )
    hits = {
        "u-1": _hit("u-1", 0.9),
        "u-2": _hit("u-2", 0.5),
    }

    ranked = ranker.rank(
        units,
        hits=hits,
        query_time="2026-01-02T00:00:00+00:00",
        recency_policy="historical",
        limit=None,
    )

    # historical: relevance only, so u-1 should win
    assert ranked[0].unit.unit_id == "u-1"
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2


def test_rank_recency_policy_balanced_favors_recent_when_relevance_close() -> None:
    ranker = MemoryUnitRanker()
    units = (
        _unit("u-old", "older relevant", "2024-01-01T00:00:00+00:00"),
        _unit("u-new", "newer relevant", "2026-01-01T00:00:00+00:00"),
    )
    hits = {
        "u-old": _hit("u-old", 0.5),
        "u-new": _hit("u-new", 0.5),
    }

    ranked = ranker.rank(
        units,
        hits=hits,
        query_time="2026-01-02T00:00:00+00:00",
        recency_policy="balanced",
        limit=None,
    )

    # balanced: newer should rank higher when relevance is tied
    assert ranked[0].unit.unit_id == "u-new"


def test_rank_limit_caps_returned_units() -> None:
    ranker = MemoryUnitRanker()
    units = tuple(
        _unit(f"u-{i}", f"fact {i}", "2026-01-01T00:00:00+00:00")
        for i in range(5)
    )
    hits = {f"u-{i}": _hit(f"u-{i}", 0.9 - 0.1 * i) for i in range(5)}

    ranked = ranker.rank(
        units,
        hits=hits,
        query_time="2026-01-02T00:00:00+00:00",
        recency_policy="balanced",
        limit=3,
    )

    assert len(ranked) == 3
    assert [r.rank for r in ranked] == [1, 2, 3]


def test_rank_score_breakdown_includes_relevance_and_recency() -> None:
    ranker = MemoryUnitRanker()
    units = (_unit("u-1", "fact", "2026-01-01T00:00:00+00:00"),)
    hits = {"u-1": _hit("u-1", 0.7)}

    ranked = ranker.rank(
        units,
        hits=hits,
        query_time="2026-01-02T00:00:00+00:00",
        recency_policy="balanced",
        limit=None,
    )

    breakdown = ranked[0].score_breakdown
    assert "relevance" in breakdown
    assert "recency" in breakdown
    assert breakdown["recency_policy"] == "balanced"
