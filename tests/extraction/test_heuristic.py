from __future__ import annotations

from nanomem.contracts import (
    CaptureDialogue,
    Dialogue,
    DialogueMessage,
    ExtractionRequest,
    MemoryScope,
)
from nanomem.extraction.heuristic import HeuristicMemoryUnitExtractor


def _request(messages: tuple[DialogueMessage, ...]) -> ExtractionRequest:
    occurred_at = "2026-01-01T00:00:00+00:00"
    dialogue = Dialogue(
        dialogue_id="dlg-1",
        session_id=None,
        messages=messages,
        started_at=occurred_at,
        ended_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    return ExtractionRequest(
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        dialogue=dialogue,
        extraction_time="2026-01-01T00:00:01+00:00",
    )


def test_extracts_personal_preference_from_user_message() -> None:
    extractor = HeuristicMemoryUnitExtractor()
    result = extractor.extract(
        _request(
            (
                DialogueMessage(
                    role="user",
                    content="I prefer concise Chinese answers.",
                    timestamp="2026-01-01T00:00:00+00:00",
                ),
            )
        )
    )

    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.scope == MemoryScope(owner_id="user-1", namespace="personal")
    assert unit.memory_type == "preference"
    assert unit.text == "I prefer concise Chinese answers."
    assert unit.metadata["extractor"] == "heuristic_v1"


def test_skips_workspace_only_message_with_no_personal_signal() -> None:
    extractor = HeuristicMemoryUnitExtractor()
    result = extractor.extract(
        _request(
            (
                DialogueMessage(
                    role="user",
                    content="See the readme and the test command in docs/.",
                    timestamp="2026-01-01T00:00:00+00:00",
                ),
            )
        )
    )

    assert result.units == ()
    assert len(result.skipped) == 1
    assert result.skipped[0].reason == "workspace_fact"


def test_skips_low_signal_user_message() -> None:
    extractor = HeuristicMemoryUnitExtractor()
    result = extractor.extract(
        _request(
            (
                DialogueMessage(
                    role="user",
                    content="The weather is fine.",
                    timestamp="2026-01-01T00:00:00+00:00",
                ),
            )
        )
    )

    assert result.units == ()
    assert len(result.skipped) == 1
    assert result.skipped[0].reason == "low_personal_signal"


def test_extracts_correction_memory_type_from_chinese_negative() -> None:
    extractor = HeuristicMemoryUnitExtractor()
    result = extractor.extract(
        _request(
            (
                DialogueMessage(
                    role="user",
                    content="不要自动提交代码，记住这点。",
                    timestamp="2026-01-01T00:00:00+00:00",
                ),
            )
        )
    )

    assert len(result.units) >= 1
    assert any(unit.memory_type == "correction" for unit in result.units)


def test_assistant_reply_with_remembering_phrase_extracts_unit() -> None:
    extractor = HeuristicMemoryUnitExtractor()
    result = extractor.extract(
        _request(
            (
                DialogueMessage(
                    role="assistant",
                    content="I will remember to keep responses concise.",
                    timestamp="2026-01-01T00:00:00+00:00",
                    metadata={"is_final": True},
                ),
            )
        )
    )

    assert len(result.units) == 1
    assert result.units[0].metadata["source_role"] == "assistant"


def test_hidden_message_is_skipped() -> None:
    extractor = HeuristicMemoryUnitExtractor()
    result = extractor.extract(
        _request(
            (
                DialogueMessage(
                    role="user",
                    content="I prefer concise answers.",
                    timestamp="2026-01-01T00:00:00+00:00",
                    metadata={"hidden": True},
                ),
            )
        )
    )

    assert result.units == ()
    assert len(result.skipped) == 1
    assert result.skipped[0].reason in {"hidden_or_tool_message", "invalid_role"}
