from __future__ import annotations

from typing import Protocol


class EmbeddingModel(Protocol):
    name: str

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        ...
