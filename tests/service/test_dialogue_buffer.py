from __future__ import annotations

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
