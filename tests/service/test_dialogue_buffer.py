from __future__ import annotations

import pytest

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    DialogueWindowSelector,
    FlushRequest,
    MemoryScope,
    ReadRequest,
)
from nanomem.service.core import NanoMemService


def test_session_capture_appends_open_dialogue_until_flush() -> None:
    service = NanoMemService(max_dialogue_tokens=512)
    scope = MemoryScope(owner_id="user-1", namespace="personal")

    first = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-1",
            dialogue=_dialogue("I prefer concise Chinese answers.", "2026-01-01"),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )
    second = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-1",
            dialogue=_dialogue("I usually want Markdown bullet points.", "2026-01-02"),
            capture_time="2026-01-02T00:00:01+00:00",
        )
    )

    assert first.unit_count == 0
    assert second.unit_count == 0
    assert second.dialogue_id == first.dialogue_id

    open_windows = service.store.query_dialogue_windows(
        DialogueWindowSelector(
            session_id="session-1",
            statuses=("open",),
        )
    )
    assert len(open_windows) == 1
    buffered_dialogue = service.store.get_dialogue(open_windows[0].dialogue_id)
    assert buffered_dialogue is not None
    assert len(buffered_dialogue.messages) == 2

    flushed = service.flush(FlushRequest(scope=scope, session_id="session-1"))

    assert flushed.dialogue_count == 1
    assert flushed.unit_count == 2
    assert service.store.query_dialogue_windows(
        DialogueWindowSelector(
            session_id="session-1",
            statuses=("open",),
        )
    ) == ()

    read = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="Markdown bullet points",
            query_time="2026-01-03T00:00:00+00:00",
        )
    )
    assert read.context.unit_count >= 1
    assert "Markdown bullet points" in read.context.text


def test_session_windows_are_isolated_across_interleaved_sessions() -> None:
    service = NanoMemService(max_dialogue_tokens=512)
    scope = MemoryScope(owner_id="user-1", namespace="personal")

    first_a = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-a",
            dialogue=_dialogue("I prefer compact answers.", "2026-01-01"),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )
    first_b = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-b",
            dialogue=_dialogue("I like examples in Python.", "2026-01-02"),
            capture_time="2026-01-02T00:00:01+00:00",
        )
    )
    second_a = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-a",
            dialogue=_dialogue("I usually want tradeoffs included.", "2026-01-03"),
            capture_time="2026-01-03T00:00:01+00:00",
        )
    )

    assert first_a.unit_count == 0
    assert first_b.unit_count == 0
    assert second_a.unit_count == 0
    assert second_a.dialogue_id == first_a.dialogue_id
    assert first_b.dialogue_id != first_a.dialogue_id

    window_a = service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-a", statuses=("open",))
    )[0]
    window_b = service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-b", statuses=("open",))
    )[0]
    dialogue_a = service.store.get_dialogue(window_a.dialogue_id)
    dialogue_b = service.store.get_dialogue(window_b.dialogue_id)

    assert dialogue_a is not None
    assert dialogue_b is not None
    assert [message.content for message in dialogue_a.messages] == [
        "I prefer compact answers.",
        "I usually want tradeoffs included.",
    ]
    assert [message.content for message in dialogue_b.messages] == [
        "I like examples in Python.",
    ]


def test_flush_extracts_only_requested_session() -> None:
    service = NanoMemService(max_dialogue_tokens=512)
    scope = MemoryScope(owner_id="user-1", namespace="personal")

    service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-a",
            dialogue=_dialogue("I prefer compact answers.", "2026-01-01"),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )
    service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-b",
            dialogue=_dialogue("I like examples in Python.", "2026-01-02"),
            capture_time="2026-01-02T00:00:01+00:00",
        )
    )

    flushed = service.flush(FlushRequest(scope=scope, session_id="session-a"))

    assert flushed.dialogue_count == 1
    assert [unit.text for unit in flushed.units] == ["I prefer compact answers."]
    assert service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-a", statuses=("open",))
    ) == ()
    assert len(
        service.store.query_dialogue_windows(
            DialogueWindowSelector(session_id="session-b", statuses=("open",))
        )
    ) == 1

    read_b = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="examples in Python",
            query_time="2026-01-03T00:00:00+00:00",
        )
    )
    assert "examples in Python" not in read_b.context.text


def test_flush_requires_session_and_scope_when_pending_windows_exist() -> None:
    service = NanoMemService(max_dialogue_tokens=512)
    scope = MemoryScope(owner_id="user-1", namespace="personal")
    service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-1",
            dialogue=_dialogue("I prefer compact answers.", "2026-01-01"),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )

    with pytest.raises(ValueError, match="session_id is required"):
        service.flush(FlushRequest())

    with pytest.raises(ValueError, match="scope is required"):
        service.flush(FlushRequest(session_id="session-1"))


def test_session_capture_seals_when_dialogue_token_limit_is_reached() -> None:
    service = NanoMemService(max_dialogue_tokens=4)
    scope = MemoryScope(owner_id="user-1", namespace="personal")

    result = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-1",
            dialogue=_dialogue("I prefer concise Chinese answers.", "2026-01-01"),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )

    assert result.unit_count == 1
    assert result.stats["dialogue_status"] == "extracted"
    assert service.store.query_dialogue_windows(
        DialogueWindowSelector(
            session_id="session-1",
            statuses=("open",),
        )
    ) == ()


def test_capture_after_token_limit_starts_new_dialogue_window() -> None:
    service = NanoMemService(max_dialogue_tokens=8)
    scope = MemoryScope(owner_id="user-1", namespace="personal")

    extracted = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-1",
            dialogue=_dialogue("I prefer concise Chinese answers.", "2026-01-01"),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )
    buffered = service.capture(
        CaptureRequest(
            scope=scope,
            session_id="session-1",
            dialogue=_dialogue("OK.", "2026-01-02"),
            capture_time="2026-01-02T00:00:01+00:00",
        )
    )

    assert extracted.unit_count == 1
    assert buffered.unit_count == 0
    assert buffered.dialogue_id != extracted.dialogue_id

    extracted_windows = service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-1", statuses=("extracted",))
    )
    open_windows = service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-1", statuses=("open",))
    )
    assert len(extracted_windows) == 1
    assert extracted_windows[0].seal_reason == "token_limit"
    assert len(open_windows) == 1
    assert open_windows[0].dialogue_id == buffered.dialogue_id


def _dialogue(content: str, day: str) -> CaptureDialogue:
    return CaptureDialogue(
        occurred_at=f"{day}T00:00:00+00:00",
        messages=(
            DialogueMessage(
                role="user",
                content=content,
                timestamp=f"{day}T00:00:00+00:00",
            ),
        ),
    )
