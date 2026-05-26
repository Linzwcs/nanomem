"""LLM-backed extractor that turns a Dialogue into MemoryUnits in one call.

The extractor's contract is: **one Dialogue is one extraction unit.**
The caller decides the dialogue boundary (capture / flush / session
window). The extractor:

1. Filters out hidden / tool / empty messages.
2. Sends the visible messages as a single LLM call.
3. Parses the JSON payload into MemoryUnits + CaptureSkips.

If a dialogue is too long for the underlying model's context window,
the model's own error propagates — the caller is responsible for not
handing the extractor an oversized dialogue (use ``flush()`` between
sessions, or capture in narrower windows).

The module composes:

- :mod:`nanomem.pipeline.representation.llm.client` to call the model.
- :mod:`nanomem.pipeline.representation.llm.parsing` to validate and
  transform the JSON payload into :class:`~nanomem.core.contracts.MemoryUnit`
  and :class:`~nanomem.core.contracts.CaptureSkip` records.

Each call to :meth:`extract` is independent; the extractor holds no
per-request state beyond configuration.
"""

from __future__ import annotations

import json
import os
from typing import Any

from nanomem.core.contracts import (
    CaptureSkip,
    DialogueMessage,
    DialogueRef,
    ExtractionRequest,
    ExtractionResult,
    MemoryUnit,
)
from nanomem.core.errors import ConfigError
from nanomem.core.ids import scope_payload, stable_id
from nanomem.pipeline.representation.base import MemoryUnitExtractor
from nanomem.pipeline.representation.events import (
    is_extractable_message,
    non_extractable_message_skip,
)
from nanomem.pipeline.representation.llm.client import (
    LLMCompletionClient,
    OpenAIChatCompletionClient,
)
from nanomem.pipeline.representation.llm.parsing import (
    LLMExtractionPayloadError,
    handle_invalid,
    is_extractable_range,
    message_range as parse_message_range,
    optional_metadata,
    range_within_indexes,
    timestamp_for_range,
    with_fallback_stats,
)
from nanomem.pipeline.representation.prompts import (
    ALLOWED_MEMORY_TYPES,
    LLM_EXTRACTION_PROMPT,
    LLM_EXTRACTION_PROMPT_VERSION,
)


class LLMMemoryUnitExtractor:
    """OpenAI-compatible extractor with an optional local fallback.

    Sends one LLM call per dialogue. No internal chunking — that is the
    caller's responsibility, expressed via dialogue boundaries.
    """

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
        strict_schema: bool = True,
    ) -> None:
        self.model = model
        self.api_key = api_key or (os.getenv(api_key_env) if api_key_env else None)
        self.base_url = base_url
        self.fallback = fallback
        self.completion_client = completion_client
        self.strict_schema = strict_schema

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

        if self.completion_client is None and not self.api_key:
            if self.fallback is not None:
                return with_fallback_stats(
                    self.fallback.extract(request),
                    reason="missing_api_key",
                )
            raise ConfigError("LLMMemoryUnitExtractor requires api_key or api_key_env")

        try:
            payload = self._complete(request, visible_messages=visible_messages)
        except Exception:
            if self.fallback is not None:
                return with_fallback_stats(
                    self.fallback.extract(request),
                    reason="llm_error",
                )
            raise

        try:
            parsed = self._parse_payload(
                payload,
                request=request,
                allowed_indexes=tuple(index for index, _ in visible_messages),
            )
        except LLMExtractionPayloadError:
            if self.fallback is not None:
                return with_fallback_stats(
                    self.fallback.extract(request),
                    reason="invalid_payload",
                )
            raise

        all_skipped = (*skipped, *parsed.skipped)
        return ExtractionResult(
            units=parsed.units,
            skipped=all_skipped,
            stats={
                "extractor": self.name,
                "model": self.model,
                "unit_count": len(parsed.units),
                "skipped_count": len(all_skipped),
                "visible_message_count": len(visible_messages),
            },
        )

    def _complete(
        self,
        request: ExtractionRequest,
        *,
        visible_messages: tuple[tuple[int, DialogueMessage], ...],
    ) -> dict[str, Any]:
        client = self.completion_client or OpenAIChatCompletionClient(
            api_key=str(self.api_key),
            base_url=self.base_url,
        )
        messages = (
            {
                "role": "system",
                "content": LLM_EXTRACTION_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "scope": scope_payload(request.scope),
                        "dialogue_id": request.dialogue.dialogue_id,
                        "messages": [
                            {
                                "index": index,
                                "role": message.role,
                                "speaker_id": message.speaker_id,
                                "content": message.content,
                                "timestamp": message.timestamp,
                            }
                            for index, message in visible_messages
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        )
        return client.complete(model=self.model, messages=messages)

    def _parse_payload(
        self,
        payload: dict[str, Any],
        *,
        request: ExtractionRequest,
        allowed_indexes: tuple[int, ...],
    ) -> ExtractionResult:
        units: list[MemoryUnit] = []
        skipped: list[CaptureSkip] = []
        for item in payload.get("units", ()):
            if not isinstance(item, dict):
                handle_invalid(
                    skipped,
                    reason="invalid_unit",
                    detail="unit item must be an object",
                    strict=self.strict_schema,
                )
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                handle_invalid(
                    skipped,
                    reason="empty_unit_text",
                    detail="unit text is required",
                    strict=self.strict_schema,
                )
                continue
            raw_message_range = item.get("message_range")
            mr = (
                None
                if raw_message_range is None
                else parse_message_range(
                    raw_message_range,
                    message_count=len(request.dialogue.messages),
                    strict=self.strict_schema,
                )
            )
            if mr is not None and not is_extractable_range(request, mr):
                handle_invalid(
                    skipped,
                    message_range_value=mr,
                    reason="non_extractable_message_range",
                    detail="message_range includes hidden, tool, or empty content",
                    strict=self.strict_schema,
                )
                continue
            if mr is not None and not range_within_indexes(mr, allowed_indexes):
                handle_invalid(
                    skipped,
                    message_range_value=mr,
                    reason="message_range_out_of_visible_set",
                    detail="message_range references filtered (hidden/tool) messages",
                    strict=self.strict_schema,
                )
                continue
            memory_type = str(item.get("memory_type", "uncertain"))
            if memory_type not in ALLOWED_MEMORY_TYPES:
                handle_invalid(
                    skipped,
                    message_range_value=mr,
                    reason="invalid_memory_type",
                    detail=f"unsupported memory_type: {memory_type}",
                    strict=self.strict_schema,
                )
                continue
            timestamp = timestamp_for_range(request, mr)
            dialogue_ref = DialogueRef(
                dialogue_id=request.dialogue.dialogue_id,
                message_range=mr,
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
                    available_at=request.extraction_time or request.dialogue.updated_at,
                    dialogue_refs=(dialogue_ref,),
                    metadata={
                        "extractor": self.name,
                        "model": self.model,
                        "prompt_version": LLM_EXTRACTION_PROMPT_VERSION,
                        **optional_metadata(item),
                    },
                )
            )
        for item in payload.get("skipped", ()):
            if not isinstance(item, dict):
                continue
            mr = parse_message_range(
                item.get("message_range"),
                message_count=len(request.dialogue.messages),
                strict=False,
            )
            if mr is not None and not range_within_indexes(mr, allowed_indexes):
                mr = None
            skipped.append(
                CaptureSkip(
                    message_range=mr,
                    reason=str(item.get("reason", "llm_skipped")),
                    detail=(str(item.get("detail")) if item.get("detail") else None),
                )
            )
        return ExtractionResult(
            units=tuple(units),
            skipped=tuple(skipped),
            stats={},
        )


def _extractable_messages(
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


__all__ = ["LLMMemoryUnitExtractor"]
