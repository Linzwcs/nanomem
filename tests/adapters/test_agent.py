from __future__ import annotations

from nanomem.adapters.agent import AgentMemoryAdapter, AgentMessage
from nanomem.contracts import MemoryScope
from nanomem.service.core import NanoMemService


def test_agent_message_round_trip_through_adapter() -> None:
    service = NanoMemService()
    adapter = AgentMemoryAdapter(
        backend=service,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
    )

    capture = adapter.capture_messages(
        (
            AgentMessage(
                role="user",
                content="I prefer concise Chinese answers.",
                timestamp="2026-01-01T00:00:00+00:00",
                speaker_id="user-1",
            ),
        ),
        capture_time="2026-01-01T00:00:01+00:00",
        occurred_at="2026-01-01T00:00:00+00:00",
    )

    assert capture.unit_count == 1


def test_before_turn_returns_empty_context_with_no_prior_memory() -> None:
    service = NanoMemService()
    adapter = AgentMemoryAdapter(
        backend=service,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
    )

    context = adapter.before_turn(
        "What's my preferred language?",
        query_time="2026-01-01T00:00:00+00:00",
    )

    assert context == ""


def test_after_turn_captures_user_message_only_by_default() -> None:
    service = NanoMemService()
    adapter = AgentMemoryAdapter(
        backend=service,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
    )

    result = adapter.after_turn(
        "I prefer concise Chinese answers.",
        assistant_message="Got it, I'll keep responses brief.",
        timestamp="2026-01-01T00:00:00+00:00",
    )

    assert result.unit_count >= 1
    sources = {
        unit.metadata.get("source_role")
        for unit in result.units
    }
    assert sources == {"user"}


def test_after_turn_with_capture_assistant_includes_assistant_facts() -> None:
    service = NanoMemService()
    adapter = AgentMemoryAdapter(
        backend=service,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
    )

    result = adapter.after_turn(
        "I prefer concise Chinese answers.",
        assistant_message="I will remember to keep responses concise.",
        timestamp="2026-01-01T00:00:00+00:00",
        capture_assistant=True,
    )

    sources = {
        unit.metadata.get("source_role")
        for unit in result.units
    }
    # Both user and assistant contributions accepted
    assert "user" in sources
    assert "assistant" in sources


def test_read_context_returns_string_payload() -> None:
    service = NanoMemService()
    adapter = AgentMemoryAdapter(
        backend=service,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
    )
    adapter.capture_messages(
        (
            AgentMessage(
                role="user",
                content="I prefer concise Chinese answers.",
                timestamp="2026-01-01T00:00:00+00:00",
            ),
        ),
        capture_time="2026-01-01T00:00:01+00:00",
        occurred_at="2026-01-01T00:00:00+00:00",
    )

    context = adapter.read_context(
        "concise Chinese answers",
        query_time="2026-01-02T00:00:00+00:00",
    )

    assert isinstance(context, str)
    assert "Chinese" in context
