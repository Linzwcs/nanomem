"""Result payloads and retrieval-side derived types.

Outputs of ``capture``, ``read``, ``flush``, the extraction pipeline,
the reindex pipeline, and the index search interface.

Note that :class:`PackedContext` is the final rendered evidence block
that reaches the downstream agent — keep its shape stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import MemoryUnit
from .requests import ReadRequest


@dataclass(frozen=True)
class CaptureSkip:
    message_range: tuple[int, int] | None
    reason: str
    detail: str | None = None


@dataclass(frozen=True)
class CaptureResult:
    dialogue_id: str
    accepted_message_count: int
    unit_count: int
    units: tuple[MemoryUnit, ...]
    skipped: tuple[CaptureSkip, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)
    trace_ref: str | None = None


@dataclass(frozen=True)
class RankedMemoryUnit:
    unit: MemoryUnit
    rank: int
    score: float
    retrieval_text: str
    score_breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PackedContext:
    text: str
    token_count: int
    unit_count: int = 0


@dataclass(frozen=True)
class ReadResult:
    request: ReadRequest
    ranked_units: tuple[RankedMemoryUnit, ...]
    context: PackedContext
    stats: dict[str, Any] = field(default_factory=dict)
    trace_ref: str | None = None


@dataclass(frozen=True)
class ReindexResult:
    indexed_unit_count: int
    index_backend: str
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FlushResult:
    dialogue_count: int
    unit_count: int
    units: tuple[MemoryUnit, ...]
    skipped: tuple[CaptureSkip, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionResult:
    units: tuple[MemoryUnit, ...]
    skipped: tuple[CaptureSkip, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexHit:
    unit_id: str
    score: float
    retrieval_text: str
    score_breakdown: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "CaptureResult",
    "CaptureSkip",
    "ExtractionResult",
    "FlushResult",
    "IndexHit",
    "PackedContext",
    "RankedMemoryUnit",
    "ReadResult",
    "ReindexResult",
]
