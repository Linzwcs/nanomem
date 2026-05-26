"""LLM completion-client surface.

Defines the :class:`LLMCompletionClient` Protocol that the extractor
depends on, plus the :class:`OpenAIChatCompletionClient` reference
implementation. Implement the Protocol elsewhere to plug in a
different provider (Anthropic, vLLM, local llama.cpp server, ...).
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from nanomem.core.errors import ExtractionError


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
            raise ExtractionError("LLM extractor response must be a JSON object")
        return parsed


__all__ = [
    "LLMCompletionClient",
    "OpenAIChatCompletionClient",
]
