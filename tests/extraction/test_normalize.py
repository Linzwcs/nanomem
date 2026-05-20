from __future__ import annotations

from nanomem.contracts import (
    DialogueMessage,
    DialogueRecord,
    ExtractionRequest,
    MemoryScope,
)
from nanomem.extraction.heuristic import HeuristicMemoryUnitExtractor
from nanomem.extraction.normalize import normalize_memory_text


def test_normalize_user_first_person_preference() -> None:
    message = _message("user", "I prefer concise Chinese answers.")

    assert normalize_memory_text(message.content, message) == (
        "The user said they prefer concise Chinese answers."
    )


def test_normalize_user_request_to_agent() -> None:
    message = _message("user", "Please include source citations.")

    assert normalize_memory_text(message.content, message) == (
        "The user asked the agent to include source citations."
    )


def test_normalize_assistant_reply_about_user() -> None:
    message = _message(
        "assistant",
        "I will remember that you prefer concise Chinese answers.",
    )

    assert normalize_memory_text(message.content, message) == (
        "The agent said it will remember that the user prefers concise "
        "Chinese answers."
    )


def test_heuristic_extractor_outputs_objective_memory_text() -> None:
    result = HeuristicMemoryUnitExtractor().extract(
        ExtractionRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=DialogueRecord(
                dialogue_id="dlg-1",
                messages=(
                    _message("user", "I prefer concise Chinese answers."),
                    _message("user", "Please include source citations."),
                ),
                captured_at="2026-01-01T00:00:10+00:00",
                occurred_at="2026-01-01T00:00:00+00:00",
            ),
        )
    )

    assert [unit.text for unit in result.units] == [
        "The user said they prefer concise Chinese answers.",
        "The user asked the agent to include source citations.",
    ]


def _message(role: str, content: str) -> DialogueMessage:
    return DialogueMessage(
        role=role,
        content=content,
        timestamp="2026-01-01T00:00:00+00:00",
    )
