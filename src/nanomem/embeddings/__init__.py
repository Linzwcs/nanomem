"""Deprecated re-export shim.

This module re-exports embedding classes from their new home at
:mod:`nanomem.index.embeddings`. Import from the new location for new
code.

This shim is kept for one alpha release cycle and may be removed in a
later version.
"""

from __future__ import annotations

import warnings

from nanomem.index.embeddings.base import EmbeddingModel
from nanomem.index.embeddings.hashing import HashingEmbeddingModel
from nanomem.index.embeddings.openai_compatible import OpenAICompatibleEmbeddingModel


warnings.warn(
    "nanomem.embeddings has moved to nanomem.index.embeddings. "
    "This shim will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)


__all__ = [
    "EmbeddingModel",
    "HashingEmbeddingModel",
    "OpenAICompatibleEmbeddingModel",
]
