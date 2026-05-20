from __future__ import annotations

from dataclasses import dataclass
import json
import os
from math import isfinite
from typing import Any, Protocol

from nanomem.contracts import (
    CaptureSkip,
    DialogueRef,
    DialogueMessage,
    ExtractionRequest,
    ExtractionResult,
    MemoryUnit,
)
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.events import (
    is_extractable_message,
    non_extractable_message_skip,
)
from nanomem.ids import scope_payload, stable_id


ALLOWED_MEMORY_TYPES = {
    "preference",
    "correction",
    "habit",
    "background",
    "relationship",
    "user_event",
    "agent_interaction_event",
    "uncertain",
}


DEFAULT_MAX_MESSAGES_PER_CHUNK = 24


@dataclass(frozen=True)
class ExtractionChunk:
    chunk_id: int
    messages: tuple[tuple[int, DialogueMessage], ...]


LLM_EXTRACTION_PROMPT = """
Extract durable long-term personal memory units from the visible dialogue.

Return JSON only:
{
  "units": [
    {
      "text": "...",
      "message_range": [0, 1],
      "memory_type": "preference|correction|habit|background|relationship|user_event|agent_interaction_event|uncertain",
      "confidence": 0.0
    }
  ],
  "skipped": [
    {"message_range": [0, 1], "reason": "...", "detail": "..."}
  ]
}

Rules:
- Extract only user-related durable personal facts.
- Use third-person, evidence-grounded wording.
- Only the visible extractable messages are provided; do not infer hidden/tool content.
- Do not extract project docs, code facts, logs, current task state, or raw tool output.
- Do not resolve conflicts or synthesize a canonical profile.
- Every unit must include a valid half-open message_range over the provided original indexes.
- A message_range must cover only contiguous provided messages; do not span omitted indexes.
""".strip()


class LLMCompletionClient(Protocol):
    def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
    ) -> dict[str, Any]:
        ...


class OpenAIChatCompletionClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
    ) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency guard
            raise RuntimeError(
                "LLMMemoryUnitExtractor requires the openai package"
            ) from exc

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        response = OpenAI(**client_kwargs).chat.completions.create(
            model=model,
            temperature=0,
            messages=list(messages),
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM extractor response must be a JSON object")
        return parsed


class LLMExtractionPayloadError(ValueError):
    pass


class LLMMemoryUnitExtractor:
    """OpenAI-compatible extractor with an optional local fallback."""

    name = "llm_v1"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = None,
        base_url: str | None = None,
        fallback: MemoryUnitExtractor | None = None,
        completion_client: LLMCompletionClient | None = None,
        confidence_threshold: float | None = None,
        strict_schema: bool = True,
        max_messages_per_chunk: int | None = DEFAULT_MAX_MESSAGES_PER_CHUNK,
        max_chars_per_chunk: int | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or (os.getenv(api_key_env) if api_key_env else None)
        self.base_url = base_url
        self.fallback = fallback
        self.completion_client = completion_client
        self.confidence_threshold = confidence_threshold
        self.strict_schema = strict_schema
        self.max_messages_per_chunk = _positive_int_or_none(
            max_messages_per_chunk,
            field_name="max_messages_per_chunk",
        )
        self.max_chars_per_chunk = _positive_int_or_none(
            max_chars_per_chunk,
            field_name="max_chars_per_chunk",
        )

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        visible_messages, skipped = _extractable_messages(request)
        if not visible_messages:
            return ExtractionResult(
                units=(),
                skipped=tuple(skipped),
                stats={
                    "extractor": self.name,
                    "model": self.model,
                    "unit_count": 0,
                    "skipped_count": len(skipped),
                    "visible_message_count": 0,
                },
            )

        chunks = _message_chunks(
            visible_messages,
            max_messages_per_chunk=self.max_messages_per_chunk,
            max_chars_per_chunk=self.max_chars_per_chunk,
        )
        if self.completion_client is None and not self.api_key:
            if self.fallback is not None:
                return _with_fallback_stats(
                    self.fallback.extract(request),
                    reason="missing_api_key",
                )
            raise RuntimeError("LLMMemoryUnitExtractor requires api_key or api_key_env")

        units: list[MemoryUnit] = []
        all_skipped = list(skipped)
        for chunk in chunks:
            try:
                payload = self._complete(request, chunk=chunk)
            except Exception:
                if self.fallback is not None:
                    return _with_fallback_stats(
                        self.fallback.extract(request),
                        reason="llm_error",
                    )
                raise
            try:
                result = self._parse_payload(
                    payload,
                    request=request,
                    allowed_indexes=tuple(index for index, _ in chunk.messages),
                    chunk_id=chunk.chunk_id,
                )
            except LLMExtractionPayloadError:
                if self.fallback is not None:
                    return _with_fallback_stats(
                        self.fallback.extract(request),
                        reason="invalid_payload",
                    )
                raise
            units.extend(result.units)
            all_skipped.extend(result.skipped)

        return ExtractionResult(
            units=tuple(units),
            skipped=tuple(all_skipped),
            stats={
                "extractor": self.name,
                "model": self.model,
                "unit_count": len(units),
                "skipped_count": len(all_skipped),
                "visible_message_count": len(visible_messages),
                "chunk_count": len(chunks),
                "max_messages_per_chunk": self.max_messages_per_chunk,
                "max_chars_per_chunk": self.max_chars_per_chunk,
            },
        )

    def _complete(
        self,
        request: ExtractionRequest,
        *,
        chunk: ExtractionChunk,
    ) -> dict[str, Any]:
        client = self.completion_client or OpenAIChatCompletionClient(
            api_key=str(self.api_key),
            base_url=self.base_url,
        )
        messages = ({
            "role": "system",
            "content": LLM_EXTRACTION_PROMPT,
        }, {
            "role": "user",
            "content": json.dumps(
                {
                    "scope": scope_payload(request.scope),
                    "dialogue_id": request.dialogue.dialogue_id,
                    "chunk_id": chunk.chunk_id,
                    "messages": [
                        {
                            "index": index,
                            "role": message.role,
                            "speaker_id": message.speaker_id,
                            "content": message.content,
                            "timestamp": message.timestamp,
                        }
                        for index, message in chunk.messages
                    ],
                },
                ensure_ascii=False,
            ),
        })
        return client.complete(
            model=self.model,
            messages=messages,
        )

    def _parse_payload(
        self,
        payload: dict[str, Any],
        *,
        request: ExtractionRequest,
        allowed_indexes: tuple[int, ...],
        chunk_id: int,
    ) -> ExtractionResult:
        units: list[MemoryUnit] = []
        skipped: list[CaptureSkip] = []
        for item in payload.get("units", ()):
            if not isinstance(item, dict):
                _handle_invalid(
                    skipped,
                    reason="invalid_unit",
                    detail="unit item must be an object",
                    strict=self.strict_schema,
                )
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                _handle_invalid(
                    skipped,
                    reason="empty_unit_text",
                    detail="unit text is required",
                    strict=self.strict_schema,
                )
                continue
            message_range = _message_range(
                item.get("message_range"),
                message_count=len(request.dialogue.messages),
                strict=self.strict_schema,
            )
            if message_range is None:
                skipped.append(
                    CaptureSkip(
                        message_range=None,
                        reason="invalid_message_range",
                        detail="unit message_range is required",
                    )
                )
                continue
            if not _is_extractable_range(request, message_range):
                _handle_invalid(
                    skipped,
                    message_range=message_range,
                    reason="non_extractable_message_range",
                    detail="message_range includes hidden, tool, or empty content",
                    strict=self.strict_schema,
                )
                continue
            if not _range_within_indexes(message_range, allowed_indexes):
                _handle_invalid(
                    skipped,
                    message_range=message_range,
                    reason="out_of_chunk_message_range",
                    detail="message_range must stay inside the current chunk",
                    strict=self.strict_schema,
                )
                continue
            memory_type = str(item.get("memory_type", "uncertain"))
            if memory_type not in ALLOWED_MEMORY_TYPES:
                _handle_invalid(
                    skipped,
                    message_range=message_range,
                    reason="invalid_memory_type",
                    detail=f"unsupported memory_type: {memory_type}",
                    strict=self.strict_schema,
                )
                continue
            confidence = _confidence(
                item.get("confidence"),
                strict=self.strict_schema,
            )
            if (
                confidence is not None
                and self.confidence_threshold is not None
                and confidence < self.confidence_threshold
            ):
                skipped.append(
                    CaptureSkip(
                        message_range=message_range,
                        reason="low_confidence",
                        detail=(
                            f"confidence {confidence:.3f} below threshold "
                            f"{self.confidence_threshold:.3f}"
                        ),
                    )
                )
                continue
            timestamp = _timestamp_for_range(request, message_range)
            dialogue_ref = DialogueRef(
                dialogue_id=request.dialogue.dialogue_id,
                message_range=message_range,
            )
            unit_id = stable_id(
                "unit",
                {
                    "scope": scope_payload(request.scope),
                    "dialogue_ref": {
                        "dialogue_id": dialogue_ref.dialogue_id,
                        "message_range": dialogue_ref.message_range,
                    },
                    "text": text,
                    "timestamp": timestamp,
                },
            )
            units.append(
                MemoryUnit(
                    unit_id=unit_id,
                    scope=request.scope,
                    text=text,
                    memory_type=memory_type,
                    timestamp=timestamp,
                    available_at=request.dialogue.captured_at,
                    dialogue_refs=(dialogue_ref,),
                    confidence=confidence,
                    metadata={
                        "extractor": self.name,
                        "model": self.model,
                        "chunk_id": chunk_id,
                        **_optional_metadata(item),
                    },
                )
            )
        for item in payload.get("skipped", ()):
            if not isinstance(item, dict):
                continue
            message_range = _message_range(
                item.get("message_range"),
                message_count=len(request.dialogue.messages),
                strict=False,
            )
            if message_range is not None and not _range_within_indexes(
                message_range,
                allowed_indexes,
            ):
                message_range = None
            skipped.append(
                CaptureSkip(
                    message_range=message_range,
                    reason=str(item.get("reason", "llm_skipped")),
                    detail=(str(item.get("detail")) if item.get("detail") else None),
                )
            )
        return ExtractionResult(
            units=tuple(units),
            skipped=tuple(skipped),
            stats={
                "extractor": self.name,
                "model": self.model,
                "unit_count": len(units),
                "skipped_count": len(skipped),
                "chunk_id": chunk_id,
                "chunk_message_count": len(allowed_indexes),
            },
        )


def _timestamp_for_range(
    request: ExtractionRequest,
    message_range: tuple[int, int],
) -> str:
    start, end = message_range
    messages = request.dialogue.messages[start:end]
    if not messages:
        return request.dialogue.occurred_at
    return messages[-1].timestamp or request.dialogue.occurred_at


def _extractable_messages(
    request: ExtractionRequest,
) -> tuple[tuple[tuple[int, DialogueMessage], ...], list[CaptureSkip]]:
    visible: list[tuple[int, DialogueMessage]] = []
    skipped: list[CaptureSkip] = []
    for index, message in enumerate(request.dialogue.messages):
        if is_extractable_message(message):
            visible.append((index, message))
        else:
            skipped.append(non_extractable_message_skip(index, message))
    return tuple(visible), skipped


def _message_chunks(
    visible_messages: tuple[tuple[int, DialogueMessage], ...],
    *,
    max_messages_per_chunk: int | None,
    max_chars_per_chunk: int | None,
) -> tuple[ExtractionChunk, ...]:
    chunks: list[ExtractionChunk] = []
    current: list[tuple[int, DialogueMessage]] = []
    for segment in _role_segments(visible_messages):
        for part in _split_segment(
            segment,
            max_messages_per_chunk=max_messages_per_chunk,
            max_chars_per_chunk=max_chars_per_chunk,
        ):
            candidate = [*current, *part]
            if current and part[0][0] != current[-1][0] + 1:
                chunks.append(
                    ExtractionChunk(
                        chunk_id=len(chunks),
                        messages=tuple(current),
                    )
                )
                current = list(part)
                continue
            if current and _would_exceed(
                candidate,
                max_messages_per_chunk=max_messages_per_chunk,
                max_chars_per_chunk=max_chars_per_chunk,
            ):
                chunks.append(
                    ExtractionChunk(
                        chunk_id=len(chunks),
                        messages=tuple(current),
                    )
                )
                current = list(part)
            else:
                current = candidate
    if current:
        chunks.append(
            ExtractionChunk(
                chunk_id=len(chunks),
                messages=tuple(current),
            )
        )
    return tuple(chunks)


def _role_segments(
    visible_messages: tuple[tuple[int, DialogueMessage], ...],
) -> tuple[tuple[tuple[int, DialogueMessage], ...], ...]:
    segments: list[tuple[tuple[int, DialogueMessage], ...]] = []
    current: list[tuple[int, DialogueMessage]] = []
    previous_index: int | None = None
    for index, message in visible_messages:
        has_gap = previous_index is not None and index != previous_index + 1
        starts_exchange = message.role != "assistant" and bool(current)
        if current and (has_gap or starts_exchange):
            segments.append(tuple(current))
            current = []
        current.append((index, message))
        previous_index = index
    if current:
        segments.append(tuple(current))
    return tuple(segments)


def _split_segment(
    segment: tuple[tuple[int, DialogueMessage], ...],
    *,
    max_messages_per_chunk: int | None,
    max_chars_per_chunk: int | None,
) -> tuple[tuple[tuple[int, DialogueMessage], ...], ...]:
    parts: list[tuple[tuple[int, DialogueMessage], ...]] = []
    current: list[tuple[int, DialogueMessage]] = []
    for item in segment:
        candidate = [*current, item]
        if current and _would_exceed(
            candidate,
            max_messages_per_chunk=max_messages_per_chunk,
            max_chars_per_chunk=max_chars_per_chunk,
        ):
            parts.append(tuple(current))
            current = [item]
        else:
            current = candidate
    if current:
        parts.append(tuple(current))
    return tuple(parts)


def _would_exceed(
    messages: list[tuple[int, DialogueMessage]],
    *,
    max_messages_per_chunk: int | None,
    max_chars_per_chunk: int | None,
) -> bool:
    if max_messages_per_chunk is not None and len(messages) > max_messages_per_chunk:
        return True
    if (
        max_chars_per_chunk is not None
        and _message_chars(messages) > max_chars_per_chunk
    ):
        return True
    return False


def _message_chars(messages: list[tuple[int, DialogueMessage]]) -> int:
    return sum(len(message.content) for _, message in messages)


def _message_range(
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


def _is_extractable_range(
    request: ExtractionRequest,
    message_range: tuple[int, int],
) -> bool:
    start, end = message_range
    return all(
        is_extractable_message(message)
        for message in request.dialogue.messages[start:end]
    )


def _range_within_indexes(
    message_range: tuple[int, int],
    allowed_indexes: tuple[int, ...],
) -> bool:
    allowed = set(allowed_indexes)
    start, end = message_range
    return all(index in allowed for index in range(start, end))


def _optional_metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if item.get("evidence_role") is not None:
        metadata["evidence_role"] = str(item["evidence_role"])
    if item.get("source_speaker_id") is not None:
        metadata["source_speaker_id"] = str(item["source_speaker_id"])
    return metadata


def _handle_invalid(
    skipped: list[CaptureSkip],
    *,
    reason: str,
    detail: str,
    strict: bool,
    message_range: tuple[int, int] | None = None,
) -> None:
    if strict:
        raise LLMExtractionPayloadError(detail)
    skipped.append(
        CaptureSkip(
            message_range=message_range,
            reason=reason,
            detail=detail,
        )
    )


def _with_fallback_stats(
    result: ExtractionResult,
    *,
    reason: str,
) -> ExtractionResult:
    return ExtractionResult(
        units=result.units,
        skipped=result.skipped,
        stats={
            **result.stats,
            "llm_fallback": True,
            "llm_fallback_reason": reason,
        },
    )


def _confidence(
    value: Any,
    *,
    strict: bool,
) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        if strict:
            raise LLMExtractionPayloadError("confidence must be a number") from exc
        return None
    if not isfinite(parsed) or parsed < 0.0 or parsed > 1.0:
        if strict:
            raise LLMExtractionPayloadError("confidence must be between 0 and 1")
        return None
    return parsed


def _positive_int_or_none(value: int | None, *, field_name: str) -> int | None:
    if value is None:
        return None
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value
