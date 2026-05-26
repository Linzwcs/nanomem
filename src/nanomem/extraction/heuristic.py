from __future__ import annotations

import re

from nanomem.core.contracts import (
    CaptureSkip,
    DialogueMessage,
    DialogueRef,
    ExtractionRequest,
    ExtractionResult,
    MemoryUnit,
)
from nanomem.extraction.events import (
    is_assistant_reply,
    is_extractable_message,
    non_extractable_message_skip,
)
from nanomem.core.ids import scope_payload, stable_id


PERSONAL_SIGNAL_PATTERN = re.compile(
    r"\b(i|my|me|mine|prefer|like|dislike|usually|always|never|"
    r"remember|don't|do not|please|want|need)\b|"
    r"(我|我的|喜欢|偏好|一般|总是|不要|别|记住|希望|习惯)",
    re.IGNORECASE,
)

WORKSPACE_PATTERN = re.compile(
    r"\b(readme|agents\.md|docs?/|adr|runbook|ci log|test command|"
    r"endpoint|api endpoint|stack trace|build output|tool log)\b",
    re.IGNORECASE,
)

ASSISTANT_REPLY_FACT_PATTERN = re.compile(
    r"\b(you prefer|your preference|you like|you usually|you want|"
    r"you need|i('ll| will) remember|i('ll| will) keep|"
    r"i('ll| will) answer|i('ll| will) use)\b|"
    r"(你偏好|你的偏好|你喜欢|你希望|你需要|我会记住|"
    r"我会保持|我会用|我会按照|后续我会|以后我会)",
    re.IGNORECASE,
)

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?。！？])\s+|\n+")


class HeuristicMemoryUnitExtractor:
    """Small deterministic extractor for tests and local smoke runs."""

    name = "heuristic_v1"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        units: list[MemoryUnit] = []
        skipped: list[CaptureSkip] = []
        for index, message in enumerate(request.dialogue.messages):
            message_units, message_skips = self._extract_message(
                index,
                message,
                request=request,
            )
            units.extend(message_units)
            skipped.extend(message_skips)
        return ExtractionResult(
            units=tuple(units),
            skipped=tuple(skipped),
            stats={
                "extractor": self.name,
                "message_count": len(request.dialogue.messages),
                "unit_count": len(units),
                "skipped_count": len(skipped),
            },
        )

    def _extract_message(
        self,
        index: int,
        message: DialogueMessage,
        *,
        request: ExtractionRequest,
    ) -> tuple[list[MemoryUnit], list[CaptureSkip]]:
        if not is_extractable_message(message):
            return [], [non_extractable_message_skip(index, message)]
        content = message.content.strip()
        personal_signal = bool(PERSONAL_SIGNAL_PATTERN.search(content))
        workspace_signal = bool(WORKSPACE_PATTERN.search(content))
        if workspace_signal and not personal_signal:
            return [], [
                CaptureSkip(
                    message_range=(index, index + 1),
                    reason="workspace_fact",
                    detail="workspace-local content belongs to local files",
                )
            ]
        if not personal_signal and not is_assistant_reply(message):
            return [], [
                CaptureSkip(
                    message_range=(index, index + 1),
                    reason="low_personal_signal",
                    detail="no durable personal signal detected",
                )
            ]

        units: list[MemoryUnit] = []
        for sentence_index, sentence in enumerate(_sentences(content)):
            if not sentence or not _is_personal_sentence(sentence, message):
                continue
            dialogue_ref = DialogueRef(
                dialogue_id=request.dialogue.dialogue_id,
                message_range=None,
            )
            unit_id = stable_id(
                "unit",
                {
                    "scope": scope_payload(request.scope),
                    "dialogue_ref": {
                        "dialogue_id": dialogue_ref.dialogue_id,
                        "message_range": dialogue_ref.message_range,
                    },
                    "sentence_index": sentence_index,
                    "text": sentence,
                    "timestamp": message.timestamp,
                },
            )
            units.append(
                MemoryUnit(
                    unit_id=unit_id,
                    scope=request.scope,
                    text=sentence,
                    memory_type=_memory_type(sentence, message),
                    timestamp=message.timestamp,
                    available_at=request.extraction_time or request.dialogue.updated_at,
                    dialogue_refs=(dialogue_ref,),
                    metadata={
                        "extractor": self.name,
                        "source_role": message.role,
                        "speaker_id": message.speaker_id,
                    },
                )
            )

        if not units:
            return [], [
                CaptureSkip(
                    message_range=(index, index + 1),
                    reason="low_personal_signal",
                    detail="no personal sentence retained",
                )
            ]
        return units, []


def _sentences(content: str) -> list[str]:
    parts = SENTENCE_SPLIT_PATTERN.split(content)
    return [part.strip() for part in parts if part.strip()]


def _is_personal_sentence(sentence: str, message: DialogueMessage) -> bool:
    if message.metadata.get("memory_type") in {"correction", "preference"}:
        return True
    if is_assistant_reply(message):
        return bool(ASSISTANT_REPLY_FACT_PATTERN.search(sentence))
    return bool(PERSONAL_SIGNAL_PATTERN.search(sentence))


def _memory_type(sentence: str, message: DialogueMessage) -> str:
    configured = message.metadata.get("memory_type")
    if isinstance(configured, str) and configured:
        return configured
    text = sentence.lower()
    if (
        "don't" in text
        or "do not" in text
        or "不要" in sentence
        or "别" in sentence
    ):
        return "correction"
    if "prefer" in text or "喜欢" in sentence or "偏好" in sentence:
        return "preference"
    return "background"
