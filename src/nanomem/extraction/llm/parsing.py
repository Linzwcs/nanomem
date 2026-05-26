"""LLM-payload schema validation and parsing helpers.

The extractor receives a JSON dict from the LLM completion client. This
module is the single owner of "is this payload well-shaped?" and "what
units / skips does it imply?". The extractor's main loop consumes the
public helpers and does not inspect raw fields.
"""

from __future__ import annotations

from typing import Any

from nanomem.core.contracts import CaptureSkip, ExtractionRequest, ExtractionResult
from nanomem.core.errors import ExtractionError
from nanomem.extraction.events import is_extractable_message


class LLMExtractionPayloadError(ExtractionError, ValueError):
    """Raised when the LLM response payload violates the extraction schema.

    Inherits from both :class:`~nanomem.errors.ExtractionError` and
    :class:`ValueError` so legacy ``except ValueError`` blocks keep
    catching it while new code can prefer ``except ExtractionError``.
    """


def timestamp_for_range(
    request: ExtractionRequest,
    message_range: tuple[int, int] | None,
) -> str:
    if message_range is None:
        return (
            request.dialogue.ended_at
            or request.dialogue.updated_at
            or request.extraction_time
            or request.dialogue.started_at
        )
    start, end = message_range
    messages = request.dialogue.messages[start:end]
    if not messages:
        return request.dialogue.started_at
    return messages[-1].timestamp or request.dialogue.started_at


def message_range(
    value: Any,
    *,
    message_count: int,
    strict: bool,
) -> tuple[int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        if strict:
            raise LLMExtractionPayloadError("message_range must be a two item list")
        return None
    try:
        start = int(value[0])
        end = int(value[1])
    except (TypeError, ValueError) as exc:
        if strict:
            raise LLMExtractionPayloadError(
                "message_range values must be integers"
            ) from exc
        return None
    if start < 0 or end <= start or end > message_count:
        if strict:
            raise LLMExtractionPayloadError("message_range is out of bounds")
        return None
    return start, end


def is_extractable_range(
    request: ExtractionRequest,
    message_range_value: tuple[int, int],
) -> bool:
    start, end = message_range_value
    return all(
        is_extractable_message(message)
        for message in request.dialogue.messages[start:end]
    )


def range_within_indexes(
    message_range_value: tuple[int, int],
    allowed_indexes: tuple[int, ...],
) -> bool:
    allowed = set(allowed_indexes)
    start, end = message_range_value
    return all(index in allowed for index in range(start, end))


def optional_metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if item.get("evidence_role") is not None:
        metadata["evidence_role"] = str(item["evidence_role"])
    if item.get("source_speaker_id") is not None:
        metadata["source_speaker_id"] = str(item["source_speaker_id"])
    return metadata


def handle_invalid(
    skipped: list[CaptureSkip],
    *,
    reason: str,
    detail: str,
    strict: bool,
    message_range_value: tuple[int, int] | None = None,
) -> None:
    if strict:
        raise LLMExtractionPayloadError(detail)
    skipped.append(
        CaptureSkip(
            message_range=message_range_value,
            reason=reason,
            detail=detail,
        )
    )


def with_fallback_stats(
    result: ExtractionResult,
    *,
    reason: str,
) -> ExtractionResult:
    """Annotate an extraction result as produced by the fallback extractor."""
    return ExtractionResult(
        units=result.units,
        skipped=result.skipped,
        stats={
            **result.stats,
            "llm_fallback": True,
            "llm_fallback_reason": reason,
        },
    )


__all__ = [
    "LLMExtractionPayloadError",
    "handle_invalid",
    "is_extractable_range",
    "message_range",
    "optional_metadata",
    "range_within_indexes",
    "timestamp_for_range",
    "with_fallback_stats",
]
