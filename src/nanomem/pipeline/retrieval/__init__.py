"""Retrieval layer — finding candidate memory units.

Three concerns:

- :mod:`nanomem.pipeline.retrieval.indexes` — lexical / dense / hybrid /
  lancedb back-ends. Each implements the
  :class:`~nanomem.pipeline.retrieval.indexes.base.MemoryUnitIndex`
  Protocol and is independently swappable.
- :mod:`nanomem.pipeline.retrieval.embeddings` — embedding models that
  the dense/hybrid/lancedb backends consume.
- :mod:`nanomem.pipeline.retrieval.ranking` — combines retrieval
  relevance with recency under a chosen policy
  (``recent`` / ``balanced`` / ``historical``).
"""

from __future__ import annotations
