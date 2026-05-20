from __future__ import annotations

from nanomem.contracts import (
    DialogueMessage,
    DialogueRecord,
    ExtractionRequest,
    MemoryScope,
)
from nanomem.extraction import (
    ExpectedMemoryUnit,
    ExpectedSkip,
    ExtractionEvalCase,
    evaluate_extraction_cases,
)
from nanomem.extraction.heuristic import HeuristicMemoryUnitExtractor


def test_extraction_eval_report_matches_expected_units_and_skips() -> None:
    report = evaluate_extraction_cases(
        HeuristicMemoryUnitExtractor(),
        (
            ExtractionEvalCase(
                case_id="preference-and-tool-skip",
                request=_request(
                    (
                        _message("user", "I prefer concise Chinese answers.", 0),
                        _message("tool", "pytest output: 13 passed.", 1),
                    )
                ),
                expected_units=(
                    ExpectedMemoryUnit(
                        memory_type="preference",
                        message_range=(0, 1),
                        text_contains=("they prefer concise chinese answers",),
                        min_confidence=0.7,
                    ),
                ),
                expected_skips=(
                    ExpectedSkip(
                        reason="invalid_role",
                        message_range=(1, 2),
                    ),
                ),
            ),
        ),
    )

    assert report.passed is True
    assert report.case_count == 1
    assert report.passed_count == 1
    payload = report.to_dict()
    assert payload["results"][0]["unit_matches"][0]["passed"] is True
    assert payload["results"][0]["skip_matches"][0]["actual"]["reason"] == "invalid_role"


def test_extraction_eval_report_surfaces_missing_expected_unit() -> None:
    report = evaluate_extraction_cases(
        HeuristicMemoryUnitExtractor(),
        (
            ExtractionEvalCase(
                case_id="missing-correction",
                request=_request((_message("user", "I prefer concise answers.", 0),)),
                expected_units=(
                    ExpectedMemoryUnit(
                        memory_type="correction",
                        message_range=(0, 1),
                    ),
                ),
            ),
        ),
    )

    result = report.results[0]
    assert report.passed is False
    assert result.passed is False
    assert result.unit_matches[0].detail == "expected memory unit was not found"


def _request(messages: tuple[DialogueMessage, ...]) -> ExtractionRequest:
    return ExtractionRequest(
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        dialogue=DialogueRecord(
            dialogue_id="dlg-1",
            messages=messages,
            captured_at="2026-01-01T00:00:30+00:00",
            occurred_at="2026-01-01T00:00:00+00:00",
        ),
    )


def _message(role: str, content: str, offset: int) -> DialogueMessage:
    return DialogueMessage(
        role=role,
        content=content,
        timestamp=f"2026-01-01T00:00:{offset * 10:02d}+00:00",
    )
