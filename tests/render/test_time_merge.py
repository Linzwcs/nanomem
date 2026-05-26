from __future__ import annotations

from nanomem.core.contracts import (
    DialogueRef,
    MemoryScope,
    MemoryUnit,
    RankedMemoryUnit,
)
from nanomem.pipeline.utilization.base import Renderer
from nanomem.pipeline.utilization.time_merge import (
    TimeMergedRenderer,
    bucket_key,
    parse_timestamp,
)


def _ranked(
    unit_id: str,
    text: str,
    timestamp: str,
    *,
    rank: int = 1,
    namespace: str | None = "personal",
) -> RankedMemoryUnit:
    unit = MemoryUnit(
        unit_id=unit_id,
        scope=MemoryScope(owner_id="user-1", namespace=namespace),
        text=text,
        memory_type="background",
        timestamp=timestamp,
        available_at=timestamp,
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )
    return RankedMemoryUnit(
        unit=unit,
        rank=rank,
        score=1.0 - 0.05 * rank,
        retrieval_text=text,
        score_breakdown={},
    )


def test_satisfies_renderer_protocol() -> None:
    renderer: Renderer = TimeMergedRenderer()
    assert renderer.name == "time_merged_v1"


def test_empty_input_returns_empty_packed_context() -> None:
    packed = TimeMergedRenderer().render((), budget_tokens=100)
    assert packed.text == ""
    assert packed.unit_count == 0


def test_single_unit_renders_without_merge() -> None:
    packed = TimeMergedRenderer().render(
        (_ranked("u-1", "fact A", "2026-05-19T10:00:00+00:00"),),
        budget_tokens=200,
    )
    assert packed.unit_count == 1
    assert "2026-05-19" in packed.text
    assert "fact A" in packed.text
    # default bucket is daily, but with one item there's no "|" separator
    assert " | " not in packed.text


def test_two_units_same_day_merge_under_daily_bucket() -> None:
    ranked = (
        _ranked("u-1", "prefers concise", "2026-05-19T09:00:00+00:00", rank=1),
        _ranked("u-2", "dislikes verbose", "2026-05-19T18:30:00+00:00", rank=2),
    )
    packed = TimeMergedRenderer(time_format="%Y-%m-%d").render(ranked, budget_tokens=500)

    # Both facts present, on one line, separated by " | "
    assert "prefers concise" in packed.text
    assert "dislikes verbose" in packed.text
    assert " | " in packed.text
    assert packed.unit_count == 2
    # Only one bucket label
    assert packed.text.count("[2026-05-19") == 1


def test_minute_granularity_does_not_merge_distinct_minutes() -> None:
    ranked = (
        _ranked("u-1", "fact A", "2026-05-19T09:00:00+00:00", rank=1),
        _ranked("u-2", "fact B", "2026-05-19T18:30:00+00:00", rank=2),
    )
    packed = TimeMergedRenderer(time_format="%Y-%m-%d %H:%M").render(
        ranked, budget_tokens=500
    )

    assert " | " not in packed.text
    assert packed.unit_count == 2
    # Two distinct bucket labels for two distinct minutes
    assert "2026-05-19 09:00" in packed.text
    assert "2026-05-19 18:30" in packed.text


def test_format_granularity_controls_merge_count() -> None:
    """The user's design insight: time_format IS the bucket key.

    Same input, three time_format choices, three different merge densities.
    """
    ranked = tuple(
        _ranked(
            f"u-{i}",
            f"fact {i}",
            f"2026-05-{19 + (i // 3):02d}T{(i % 24):02d}:00:00+00:00",
            rank=i + 1,
        )
        for i in range(6)
    )

    minute = TimeMergedRenderer(time_format="%Y-%m-%d %H:%M").render(ranked, budget_tokens=2000)
    daily = TimeMergedRenderer(time_format="%Y-%m-%d").render(ranked, budget_tokens=2000)
    monthly = TimeMergedRenderer(time_format="%Y-%m").render(ranked, budget_tokens=2000)

    # Larger granularity → fewer lines (more merging).
    minute_lines = [l for l in minute.text.splitlines() if l.startswith("- [")]
    daily_lines = [l for l in daily.text.splitlines() if l.startswith("- [")]
    monthly_lines = [l for l in monthly.text.splitlines() if l.startswith("- [")]

    assert len(minute_lines) >= len(daily_lines) >= len(monthly_lines)
    # All policies retain the same total unit count.
    assert minute.unit_count == daily.unit_count == monthly.unit_count == 6


def test_different_namespaces_stay_separate_even_in_same_bucket() -> None:
    ranked = (
        _ranked(
            "u-1",
            "personal fact",
            "2026-05-19T10:00:00+00:00",
            rank=1,
            namespace="personal",
        ),
        _ranked(
            "u-2",
            "work fact",
            "2026-05-19T11:00:00+00:00",
            rank=2,
            namespace="work",
        ),
    )
    packed = TimeMergedRenderer(time_format="%Y-%m-%d").render(ranked, budget_tokens=500)

    # Same day but different namespaces → two separate group lines.
    group_lines = [l for l in packed.text.splitlines() if l.startswith("- [")]
    assert len(group_lines) == 2
    assert any("namespace=personal" in l for l in group_lines)
    assert any("namespace=work" in l for l in group_lines)


def test_unparseable_timestamp_falls_into_unknown_bucket() -> None:
    ranked = (
        _ranked("u-1", "fact A", "not a real timestamp", rank=1),
    )
    packed = TimeMergedRenderer().render(ranked, budget_tokens=200)

    assert "[unknown" in packed.text
    assert "fact A" in packed.text


def test_budget_enforces_group_atomic_packing() -> None:
    long_text = "this fact is quite long and takes many tokens " * 10
    ranked = tuple(
        _ranked(f"u-{i}", long_text, "2026-05-19T10:00:00+00:00", rank=i + 1)
        for i in range(3)
    )

    tight = TimeMergedRenderer().render(ranked, budget_tokens=30)
    loose = TimeMergedRenderer().render(ranked, budget_tokens=5000)

    assert tight.unit_count <= loose.unit_count
    assert loose.unit_count == 3
    # Tight budget either includes the whole merged group or nothing
    # (since all 3 units share the same daily bucket).
    assert tight.unit_count in {0, 3}


def test_parse_timestamp_handles_iso_with_offset() -> None:
    parsed = parse_timestamp("2026-05-19T10:00:00+08:00")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 5
    assert parsed.day == 19


def test_parse_timestamp_returns_none_for_unparseable() -> None:
    assert parse_timestamp(None) is None
    assert parse_timestamp("") is None
    assert parse_timestamp("unknown") is None
    assert parse_timestamp("not a timestamp at all") is None


def test_bucket_key_quantizes_to_format() -> None:
    ts = "2026-05-19T15:42:00+00:00"
    assert bucket_key(ts, "%Y-%m-%d") == "2026-05-19"
    assert bucket_key(ts, "%Y-%m") == "2026-05"
    assert bucket_key(ts, "%Y") == "2026"
    assert bucket_key(None, "%Y-%m-%d") == "unknown"
