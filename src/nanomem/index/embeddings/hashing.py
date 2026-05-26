from __future__ import annotations

import hashlib
import math

from nanomem.core.errors import ConfigError
from nanomem.index.embeddings.base import EmbeddingModel
from nanomem.index.lexical import tokenize


class HashingEmbeddingModel:
    """Deterministic local embedding model for tests and offline startup."""

    def __init__(self, *, dimensions: int = 128, name: str | None = None) -> None:
        if dimensions <= 0:
            raise ConfigError("HashingEmbeddingModel dimensions must be positive")
        self.dimensions = dimensions
        self.name = name or f"hashing_embedding_{dimensions}"

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._embed_one(text) for text in texts)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            return tuple(values)
        return tuple(value / norm for value in values)
