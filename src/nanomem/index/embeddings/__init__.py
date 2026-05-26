"""Embedding models used by the index backends.

This package was previously at ``nanomem.embeddings``. The new location
co-locates embedding models with the index backends that consume them
(``dense``, ``hybrid``, ``lancedb``).

Backward compatibility: ``from nanomem.embeddings import X`` still works
through a shim at the old location. Prefer the new path for new code.
"""

from __future__ import annotations

from nanomem.index.embeddings.base import EmbeddingModel
from nanomem.index.embeddings.hashing import HashingEmbeddingModel
from nanomem.index.embeddings.openai_compatible import OpenAICompatibleEmbeddingModel


__all__ = [
    "EmbeddingModel",
    "HashingEmbeddingModel",
    "OpenAICompatibleEmbeddingModel",
]
