"""Embedding models used by the retrieval indexes.

Co-located with the index backends that consume them (``dense``,
``hybrid``, ``lancedb``). Implementations satisfy the
:class:`~nanomem.pipeline.retrieval.embeddings.base.EmbeddingModel`
Protocol.
"""

from __future__ import annotations

from nanomem.pipeline.retrieval.embeddings.base import EmbeddingModel
from nanomem.pipeline.retrieval.embeddings.hashing import HashingEmbeddingModel
from nanomem.pipeline.retrieval.embeddings.openai_compatible import OpenAICompatibleEmbeddingModel


__all__ = [
    "EmbeddingModel",
    "HashingEmbeddingModel",
    "OpenAICompatibleEmbeddingModel",
]
