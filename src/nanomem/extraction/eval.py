from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nanomem.core.contracts import (
    CaptureSkip,
    ExtractionRequest,
    ExtractionResult,
    MemoryUnit,
)
from nanomem.extraction.base import MemoryUnitExtractor


@dataclass(frozen=True)
class ExpectedMemoryUnit:
    memory_type: str | None = None
    message_range: tuple[int, int] | None = None
    text: str | None = None
    text_contains: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpectedSkip:
    reason: str
    message_range: tuple[int, int] | None = None


@dataclass(frozen=True)
class ExtractionEvalCase:
    case_id: str
    request: ExtractionRequest
    expected_units: tuple[ExpectedMemoryUnit, ...] = ()
    expected_skips: tuple[ExpectedSkip, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalMatch:
    passed: bool
    expected: dict[str, Any]
    actual: dict[str, Any] | None = None
    detail: str | None = None


@dataclass(frozen=True)
class ExtractionEvalCaseResult:
    case_id: str
    passed: bool
    unit_matches: tuple[EvalMatch, ...]
    skip_matches: tuple[EvalMatch, ...]
    actual_unit_count: int
    actual_skip_count: int
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionEvalReport:
    results: tuple[ExtractionEvalCaseResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    @property
    def case_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "results": [_case_result_to_dict(result) for result in self.results],
        }


def evaluate_extraction_cases(
    extractor: MemoryUnitExtractor,
    cases: tuple[ExtractionEvalCase, ...],
) -> ExtractionEvalReport:
    return ExtractionEvalReport(
        results=tuple(evaluate_extraction_case(extractor, case) for case in cases)
    )


def evaluate_extraction_case(
    extractor: MemoryUnitExtractor,
    case: ExtractionEvalCase,
) -> ExtractionEvalCaseResult:
    result = extractor.extract(case.request)
    unit_matches = _match_units(case.expected_units, result.units)
    skip_matches = _match_skips(case.expected_skips, result.skipped)
    passed = all(match.passed for match in (*unit_matches, *skip_matches))
    return ExtractionEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        unit_matches=unit_matches,
        skip_matches=skip_matches,
        actual_unit_count=len(result.units),
        actual_skip_count=len(result.skipped),
        stats=dict(result.stats),
    )


def _match_units(
    expected_units: tuple[ExpectedMemoryUnit, ...],
    actual_units: tuple[MemoryUnit, ...],
) -> tuple[EvalMatch, ...]:
    used_indexes: set[int] = set()
    matches: list[EvalMatch] = []
    for expected in expected_units:
        match_index = _find_unit_match(expected, actual_units, used_indexes)
        if match_index is None:
            matches.append(
                EvalMatch(
                    passed=False,
                    expected=_expected_unit_payload(expected),
                    detail="expected memory unit was not found",
                )
            )
            continue
        used_indexes.add(match_index)
        matches.append(
            EvalMatch(
                passed=True,
                expected=_expected_unit_payload(expected),
                actual=_unit_payload(actual_units[match_index]),
            )
        )
    return tuple(matches)


def _find_unit_match(
    expected: ExpectedMemoryUnit,
    actual_units: tuple[MemoryUnit, ...],
    used_indexes: set[int],
) -> int | None:
    for index, unit in enumerate(actual_units):
        if index in used_indexes:
            continue
        if _unit_matches(expected, unit):
            return index
    return None


def _unit_matches(expected: ExpectedMemoryUnit, unit: MemoryUnit) -> bool:
    if expected.memory_type is not None and unit.memory_type != expected.memory_type:
        return False
    if expected.message_range is not None and not any(
        ref.message_range == expected.message_range for ref in unit.dialogue_refs
    ):
        return False
    if expected.text is not None and unit.text != expected.text:
        return False
    lowered = unit.text.lower()
    if any(fragment.lower() not in lowered for fragment in expected.text_contains):
        return False
    return True


def _match_skips(
    expected_skips: tuple[ExpectedSkip, ...],
    actual_skips: tuple[CaptureSkip, ...],
) -> tuple[EvalMatch, ...]:
    used_indexes: set[int] = set()
    matches: list[EvalMatch] = []
    for expected in expected_skips:
        match_index = _find_skip_match(expected, actual_skips, used_indexes)
        if match_index is None:
            matches.append(
                EvalMatch(
                    passed=False,
                    expected=_expected_skip_payload(expected),
                    detail="expected skip was not found",
                )
            )
            continue
        used_indexes.add(match_index)
        matches.append(
            EvalMatch(
                passed=True,
                expected=_expected_skip_payload(expected),
                actual=_skip_payload(actual_skips[match_index]),
            )
        )
    return tuple(matches)


def _find_skip_match(
    expected: ExpectedSkip,
    actual_skips: tuple[CaptureSkip, ...],
    used_indexes: set[int],
) -> int | None:
    for index, skip in enumerate(actual_skips):
        if index in used_indexes:
            continue
        if skip.reason != expected.reason:
            continue
        if expected.message_range is not None and skip.message_range != expected.message_range:
            continue
        return index
    return None


def _case_result_to_dict(result: ExtractionEvalCaseResult) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "passed": result.passed,
        "actual_unit_count": result.actual_unit_count,
        "actual_skip_count": result.actual_skip_count,
        "unit_matches": [_match_payload(match) for match in result.unit_matches],
        "skip_matches": [_match_payload(match) for match in result.skip_matches],
        "stats": result.stats,
    }


def _match_payload(match: EvalMatch) -> dict[str, Any]:
    return {
        "passed": match.passed,
        "expected": match.expected,
        "actual": match.actual,
        "detail": match.detail,
    }


def _expected_unit_payload(expected: ExpectedMemoryUnit) -> dict[str, Any]:
    return {
        "memory_type": expected.memory_type,
        "message_range": expected.message_range,
        "text": expected.text,
        "text_contains": expected.text_contains,
    }


def _expected_skip_payload(expected: ExpectedSkip) -> dict[str, Any]:
    return {
        "reason": expected.reason,
        "message_range": expected.message_range,
    }


def _unit_payload(unit: MemoryUnit) -> dict[str, Any]:
    return {
        "unit_id": unit.unit_id,
        "text": unit.text,
        "memory_type": unit.memory_type,
        "dialogue_refs": [
            {
                "dialogue_id": ref.dialogue_id,
                "message_range": ref.message_range,
            }
            for ref in unit.dialogue_refs
        ],
    }


def _skip_payload(skip: CaptureSkip) -> dict[str, Any]:
    return {
        "message_range": skip.message_range,
        "reason": skip.reason,
        "detail": skip.detail,
    }
