from __future__ import annotations

from nanomem.core.contracts import (
    DialogueRef,
    MemoryScope,
    MemoryUnit,
    RankedMemoryUnit,
)
from nanomem.pipeline.utilization.evidence_context import EvidenceContextRenderer, estimate_tokens


def _ranked(unit_id: str, text: str, timestamp: str, rank: int = 1) -> RankedMemoryUnit:
    unit = MemoryUnit(
        unit_id=unit_id,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        text=text,
        memory_type="background",
        timestamp=timestamp,
        available_at=timestamp,
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )
    return RankedMemoryUnit(
        unit=unit,
        rank=rank,
        score=1.0 - 0.1 * rank,
        retrieval_text=text,
        score_breakdown={},
    )


def test_render_includes_timestamp_and_namespace_label() -> None:
    renderer = EvidenceContextRenderer()
    packed = renderer.render(
        (_ranked("u-1", "user prefers concise answers", "2026-01-01T00:00:00+00:00"),),
        budget_tokens=200,
    )

    assert "2026-01-01T00:00:00+00:00" in packed.text
    assert "namespace=personal" in packed.text
    assert "user prefers concise answers" in packed.text
    assert packed.unit_count == 1


def test_render_returns_empty_packed_for_empty_input() -> None:
    renderer = EvidenceContextRenderer()
    packed = renderer.render((), budget_tokens=200)

    assert packed.text == ""
    assert packed.unit_count == 0
    assert packed.token_count == 0


def test_render_truncates_under_token_budget() -> None:
    renderer = EvidenceContextRenderer()
    long_text = "user prefers detail in answers " * 30
    ranked = tuple(
        _ranked(f"u-{i}", long_text, "2026-01-01T00:00:00+00:00", rank=i + 1)
        for i in range(5)
    )

    tight = renderer.render(ranked, budget_tokens=50)
    loose = renderer.render(ranked, budget_tokens=2000)

    assert tight.unit_count <= loose.unit_count
    assert tight.token_count <= 60  # close to budget, plus headroom for header
    assert loose.unit_count > 0


def test_render_no_budget_includes_all_units() -> None:
    renderer = EvidenceContextRenderer()
    ranked = (
        _ranked("u-1", "fact A", "2026-01-01T00:00:00+00:00", rank=1),
        _ranked("u-2", "fact B", "2026-01-02T00:00:00+00:00", rank=2),
    )

    packed = renderer.render(ranked, budget_tokens=None)

    assert packed.unit_count == 2


def test_estimate_tokens_handles_mixed_script() -> None:
    assert estimate_tokens("hello world") == 2
    assert estimate_tokens("你好 world") == 3
    assert estimate_tokens("") == 0
