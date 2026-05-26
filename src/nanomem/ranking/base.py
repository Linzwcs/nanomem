"""Ranker interface for the read pipeline.

A ``Ranker`` consumes loaded :class:`~nanomem.contracts.MemoryUnit` records
together with their :class:`~nanomem.contracts.IndexHit` retrieval scores
and produces an ordered sequence of :class:`~nanomem.contracts.RankedMemoryUnit`
records under a chosen recency policy.

The default implementation is
:class:`nanomem.ranking.ranker.MemoryUnitRanker`, which combines relevance
and recency under one of ``"recent"`` / ``"balanced"`` / ``"historical"``
policies.

The interface is a :class:`typing.Protocol` — implementations satisfy it
by duck typing; explicit inheritance is not required.
"""

from __future__ import annotations

from typing import Protocol

from nanomem.contracts import IndexHit, MemoryUnit, RankedMemoryUnit


class Ranker(Protocol):
    """Order memory units for the rendered evidence block.

    Implementations should:

    - drop units with zero or negative retrieval relevance;
    - return a deterministic order under tied scores;
    - assign a monotonically increasing ``rank`` starting at 1;
    - honour ``limit`` when provided.
    """

    name: str

    def rank(
        self,
        units: tuple[MemoryUnit, ...],
        *,
        hits: dict[str, IndexHit],
        query_time: str | None,
        recency_policy: str,
        limit: int | None,
    ) -> tuple[RankedMemoryUnit, ...]:
        ...


__all__ = ["Ranker"]
