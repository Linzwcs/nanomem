"""Paper-axis-aligned memory pipeline.

The four sub-packages mirror the controlled experimental axes from the
companion paper *Long-Term Personal Memory Under Budget: An
Evidence-Density Principle*:

- :mod:`nanomem.pipeline.representation` — how dialogue becomes
  memory units (heuristic, LLM-based extraction)
- :mod:`nanomem.pipeline.storage`        — where units live (sqlite)
- :mod:`nanomem.pipeline.retrieval`      — how candidates are found
  (lexical / dense / hybrid / lancedb indexes, embeddings, ranking)
- :mod:`nanomem.pipeline.utilization`    — how ranked units are packed
  for the answer LLM under a token budget

Layering rule: ``pipeline/`` modules may import from :mod:`nanomem.core`
only. They must not import :mod:`nanomem.service`,
:mod:`nanomem.transports`, :mod:`nanomem.admin`, or :mod:`nanomem.hosts`.
"""

from __future__ import annotations
