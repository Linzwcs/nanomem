"""Deprecated re-export shim — scheduled for removal in v0.3.0.

This module re-exports embedding classes from their new home at
:mod:`nanomem.index.embeddings`. Update imports to the new location:

.. code-block:: python

    # before
    from nanomem.embeddings import HashingEmbeddingModel

    # after
    from nanomem.index.embeddings import HashingEmbeddingModel

Importing from this shim emits :class:`DeprecationWarning`. The shim
itself will be deleted in v0.3.0; check
:data:`__deprecated_removal__` to confirm the planned removal version.
"""

from __future__ import annotations

import warnings

from nanomem.index.embeddings.base import EmbeddingModel
from nanomem.index.embeddings.hashing import HashingEmbeddingModel
from nanomem.index.embeddings.openai_compatible import OpenAICompatibleEmbeddingModel


__deprecated_removal__ = "0.3.0"


warnings.warn(
    "nanomem.embeddings has moved to nanomem.index.embeddings. "
    f"This shim will be removed in v{__deprecated_removal__}.",
    DeprecationWarning,
    stacklevel=2,
)


__all__ = [
    "EmbeddingModel",
    "HashingEmbeddingModel",
    "OpenAICompatibleEmbeddingModel",
]
