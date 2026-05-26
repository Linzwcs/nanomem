"""LLM-backed extractor that turns dialogue chunks into MemoryUnits.

The class composes:

- :mod:`nanomem.extraction.llm.chunking` to slice dialogues into
  per-LLM-call chunks under message/char budgets
- :mod:`nanomem.extraction.llm.client` to actually call the model
- :mod:`nanomem.extraction.llm.parsing` to validate and transform the
  JSON payload into :class:`~nanomem.contracts.MemoryUnit` and
  :class:`~nanomem.contracts.CaptureSkip` records

Each call to :meth:`extract` is independent; the extractor holds no
per-request state beyond configuration.
"""

from __future__ import annotations

import json
import os
from typing import Any

from nanomem.core.contracts import (
    CaptureSkip,
    DialogueRef,
    ExtractionRequest,
    ExtractionResult,
    MemoryUnit,
)
from nanomem.errors import ConfigError
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.llm.chunking import (
    ExtractionChunk,
    extractable_messages,
    message_chunks,
    positive_int_or_none,
)
from nanomem.extraction.llm.client import (
    LLMCompletionClient,
    OpenAIChatCompletionClient,
)
from nanomem.extraction.llm.parsing import (
    LLMExtractionPayloadError,
    handle_invalid,
    is_extractable_range,
    message_range as parse_message_range,
    optional_metadata,
    range_within_indexes,
    timestamp_for_range,
    with_fallback_stats,
)
from nanomem.extraction.prompts import (
    ALLOWED_MEMORY_TYPES,
    LLM_EXTRACTION_PROMPT,
    LLM_EXTRACTION_PROMPT_VERSION,
)
from nanomem.ids import scope_payload, stable_id


# Re-exported for backward compatibility with code that imported the
# chunking budget from `nanomem.extraction.llm`.
from nanomem.extraction.llm.chunking import (  # noqa: F401  (re-export)
    DEFAULT_MAX_MESSAGES_PER_CHUNK,
)


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
        strict_schema: bool = True,
        max_messages_per_chunk: int | None = DEFAULT_MAX_MESSAGES_PER_CHUNK,
        max_chars_per_chunk: int | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or (os.getenv(api_key_env) if api_key_env else None)
        self.base_url = base_url
        self.fallback = fallback
        self.completion_client = completion_client
        self.strict_schema = strict_schema
        self.max_messages_per_chunk = positive_int_or_none(
            max_messages_per_chunk,
            field_name="max_messages_per_chunk",
        )
        self.max_chars_per_chunk = positive_int_or_none(
            max_chars_per_chunk,
            field_name="max_chars_per_chunk",
        )

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        visible_messages, skipped = extractable_messages(request)
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

        chunks = message_chunks(
            visible_messages,
            max_messages_per_chunk=self.max_messages_per_chunk,
            max_chars_per_chunk=self.max_chars_per_chunk,
        )
        if self.completion_client is None and not self.api_key:
            if self.fallback is not None:
                return with_fallback_stats(
                    self.fallback.extract(request),
                    reason="missing_api_key",
                )
            raise ConfigError("LLMMemoryUnitExtractor requires api_key or api_key_env")

        units: list[MemoryUnit] = []
        all_skipped = list(skipped)
        for chunk in chunks:
            try:
                payload = self._complete(request, chunk=chunk)
            except Exception:
                if self.fallback is not None:
                    return with_fallback_stats(
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
                    return with_fallback_stats(
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
                    reason="out_of_chunk_message_range",
                    detail="message_range must stay inside the current chunk",
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
                        "chunk_id": chunk_id,
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
            stats={
                "extractor": self.name,
                "model": self.model,
                "unit_count": len(units),
                "skipped_count": len(skipped),
                "chunk_id": chunk_id,
                "chunk_message_count": len(allowed_indexes),
            },
        )


__all__ = [
    "DEFAULT_MAX_MESSAGES_PER_CHUNK",
    "LLMMemoryUnitExtractor",
]
