from __future__ import annotations

from nanomem.contracts import (
    DialogueRef,
    IndexHit,
    MemoryScope,
    MemoryUnit,
    RankedMemoryUnit,
)
from nanomem.ranking.base import Ranker
from nanomem.ranking.ranker import MemoryUnitRanker
from nanomem.render.base import Renderer
from nanomem.render.context import EvidenceContextRenderer


def _ranked() -> RankedMemoryUnit:
    unit = MemoryUnit(
        unit_id="u-1",
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        text="fact",
        memory_type="background",
        timestamp="2026-01-01T00:00:00+00:00",
        available_at="2026-01-01T00:00:00+00:00",
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )
    return RankedMemoryUnit(
        unit=unit,
        rank=1,
        score=0.9,
        retrieval_text="fact",
        score_breakdown={},
    )


def _unit(unit_id: str) -> MemoryUnit:
    return MemoryUnit(
        unit_id=unit_id,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        text=f"fact {unit_id}",
        memory_type="background",
        timestamp="2026-01-01T00:00:00+00:00",
        available_at="2026-01-01T00:00:00+00:00",
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )


def test_evidence_context_renderer_satisfies_renderer_protocol() -> None:
    renderer: Renderer = EvidenceContextRenderer()

    packed = renderer.render((_ranked(),), budget_tokens=200)

    assert packed.unit_count == 1
    assert renderer.name == "evidence_context_v1"


def test_memory_unit_ranker_satisfies_ranker_protocol() -> None:
    ranker: Ranker = MemoryUnitRanker()

    ranked = ranker.rank(
        (_unit("u-1"),),
        hits={"u-1": IndexHit(unit_id="u-1", score=0.8, retrieval_text="fact u-1")},
        query_time="2026-01-02T00:00:00+00:00",
        recency_policy="balanced",
        limit=None,
    )

    assert len(ranked) == 1
    assert ranked[0].rank == 1
    assert ranker.name == "relevance_recency_v1"


def test_protocols_are_importable_from_top_level() -> None:
    import nanomem

    assert nanomem.Renderer is Renderer
    assert nanomem.Ranker is Ranker
