from __future__ import annotations

import os
from typing import Any


class OpenAICompatibleEmbeddingModel:
    """Embedding model backed by an OpenAI-compatible embeddings API."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = None,
        base_url: str | None = None,
        name: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or (os.getenv(api_key_env) if api_key_env else None)
        self.base_url = base_url
        self.name = name or f"openai_compatible:{model}"
        if not self.api_key:
            raise RuntimeError(
                "OpenAICompatibleEmbeddingModel requires api_key or api_key_env"
            )

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency guard
            raise RuntimeError(
                "OpenAICompatibleEmbeddingModel requires the openai package"
            ) from exc

        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        response = OpenAI(**client_kwargs).embeddings.create(
            model=self.model,
            input=list(texts),
        )
        return tuple(tuple(float(value) for value in item.embedding)
                     for item in response.data)
