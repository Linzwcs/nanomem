"""Dialogue-message chunking for the LLM extractor.

Splits a sequence of (index, DialogueMessage) tuples into one or more
:class:`ExtractionChunk` records that fit message-count and char-count
budgets while preserving role-boundary semantics.
"""

from __future__ import annotations

from dataclasses import dataclass

from nanomem.core.contracts import CaptureSkip, DialogueMessage, ExtractionRequest
from nanomem.errors import ConfigError
from nanomem.extraction.events import (
    is_extractable_message,
    non_extractable_message_skip,
)


DEFAULT_MAX_MESSAGES_PER_CHUNK = 24


@dataclass(frozen=True)
class ExtractionChunk:
    """A contiguous slice of visible dialogue messages sent to the LLM."""

    chunk_id: int
    messages: tuple[tuple[int, DialogueMessage], ...]


def extractable_messages(
    request: ExtractionRequest,
) -> tuple[tuple[tuple[int, DialogueMessage], ...], list[CaptureSkip]]:
    """Partition request messages into visible vs. skipped."""
    visible: list[tuple[int, DialogueMessage]] = []
    skipped: list[CaptureSkip] = []
    for index, message in enumerate(request.dialogue.messages):
        if is_extractable_message(message):
            visible.append((index, message))
        else:
            skipped.append(non_extractable_message_skip(index, message))
    return tuple(visible), skipped


def message_chunks(
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


def positive_int_or_none(value: int | None, *, field_name: str) -> int | None:
    """Validate a per-chunk budget; ``None`` is allowed (no limit)."""
    if value is None:
        return None
    if value <= 0:
        raise ConfigError(f"{field_name} must be positive")
    return value


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


__all__ = [
    "DEFAULT_MAX_MESSAGES_PER_CHUNK",
    "ExtractionChunk",
    "extractable_messages",
    "message_chunks",
    "positive_int_or_none",
]
