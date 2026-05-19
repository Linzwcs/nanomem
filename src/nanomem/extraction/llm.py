from __future__ import annotations

import json
import os
from typing import Any

from nanomem.contracts import (
    CaptureSkip,
    DialogueRef,
    ExtractionRequest,
    ExtractionResult,
    MemoryUnit,
)
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.ids import scope_payload, stable_id


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
- Do not extract project docs, code facts, logs, current task state, or raw tool output.
- Do not resolve conflicts or synthesize a canonical profile.
""".strip()


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
    ) -> None:
        self.model = model
        self.api_key = api_key or (os.getenv(api_key_env) if api_key_env else None)
        self.base_url = base_url
        self.fallback = fallback

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        if not self.api_key:
            if self.fallback is not None:
                return _with_fallback_stats(
                    self.fallback.extract(request),
                    reason="missing_api_key",
                )
            raise RuntimeError("LLMMemoryUnitExtractor requires api_key or api_key_env")
        try:
            payload = self._complete(request)
        except Exception:
            if self.fallback is not None:
                return _with_fallback_stats(
                    self.fallback.extract(request),
                    reason="llm_error",
                )
            raise
        return self._parse_payload(payload, request=request)

    def _complete(self, request: ExtractionRequest) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency guard
            raise RuntimeError("LLMMemoryUnitExtractor requires the openai package") from exc

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        messages = [{
            "role": "system",
            "content": LLM_EXTRACTION_PROMPT,
        }, {
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
                        for index, message in enumerate(request.dialogue.messages)
                    ],
                },
                ensure_ascii=False,
            ),
        }]
        response = OpenAI(**client_kwargs).chat.completions.create(
            model=self.model,
            temperature=0,
            messages=messages,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM extractor response must be a JSON object")
        return parsed

    def _parse_payload(
        self,
        payload: dict[str, Any],
        *,
        request: ExtractionRequest,
    ) -> ExtractionResult:
        units: list[MemoryUnit] = []
        skipped: list[CaptureSkip] = []
        for item in payload.get("units", ()):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            message_range = _message_range(item.get("message_range"))
            if message_range is None:
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
                    memory_type=str(item.get("memory_type", "uncertain")),
                    timestamp=timestamp,
                    available_at=request.dialogue.captured_at,
                    dialogue_refs=(dialogue_ref,),
                    confidence=_float_or_none(item.get("confidence")),
                    metadata={
                        "extractor": self.name,
                        "model": self.model,
                    },
                )
            )
        for item in payload.get("skipped", ()):
            if not isinstance(item, dict):
                continue
            skipped.append(
                CaptureSkip(
                    message_range=_message_range(item.get("message_range")),
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


def _message_range(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    return (int(value[0]), int(value[1]))


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


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
