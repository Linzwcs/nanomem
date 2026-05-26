"""Renderer interface for the read pipeline.

A ``Renderer`` packs a ranked sequence of memory units into a single
``PackedContext`` block under an optional post-render token budget.

The default implementation is
:class:`nanomem.render.context.EvidenceContextRenderer`, which renders
each unit on one line with its timestamp and namespace label.

The interface is a :class:`typing.Protocol` — implementations satisfy
it by duck typing; explicit inheritance is not required.
"""

from __future__ import annotations

from typing import Protocol

from nanomem.contracts import PackedContext, RankedMemoryUnit


class Renderer(Protocol):
    """Pack ranked memory units into a single ``PackedContext`` block.

    Implementations should:

    - preserve evidence (no silent rewriting of unit text);
    - keep enough metadata for the downstream agent to reason over time
      and scope (at minimum: timestamp);
    - respect ``budget_tokens`` — never exceed it, never include a partial
      unit, and return an empty ``PackedContext`` if even one unit would
      overshoot the budget.
    """

    name: str

    def render(
        self,
        ranked: tuple[RankedMemoryUnit, ...],
        *,
        budget_tokens: int | None = None,
    ) -> PackedContext:
        ...


__all__ = ["Renderer"]
