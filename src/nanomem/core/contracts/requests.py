"""Request payloads for the agent-facing and internal pipelines.

These are the input shapes for ``capture``, ``read``, ``flush``, the
extraction pipeline, and the index search interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .core import (
    CaptureDialogue,
    Dialogue,
    MemoryScope,
    TimeRange,
)


@dataclass(frozen=True)
class CaptureRequest:
    scope: MemoryScope
    dialogue: CaptureDialogue
    capture_time: str
    session_id: str | None = None


@dataclass(frozen=True)
class ReadRequest:
    owner_id: str
    namespaces: tuple[str, ...] | None
    query: str | dict[str, Any]
    query_time: str
    time_range: TimeRange | None = None
    recency_policy: Literal["recent", "balanced", "historical"] | None = None
    max_units: int | None = None
    context_budget_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FlushRequest:
    scope: MemoryScope | None = None
    session_id: str | None = None
    flush_time: str | None = None


@dataclass(frozen=True)
class ExtractionRequest:
    scope: MemoryScope
    dialogue: Dialogue
    extraction_time: str | None = None


@dataclass(frozen=True)
class IndexSearchRequest:
    owner_id: str
    namespaces: tuple[str, ...] | None
    query: str
    time_range: TimeRange | None = None
    limit: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "CaptureRequest",
    "ExtractionRequest",
    "FlushRequest",
    "IndexSearchRequest",
    "ReadRequest",
]
