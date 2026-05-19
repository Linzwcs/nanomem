from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class MemoryScope:
    owner_id: str
    namespace: str | None = None


@dataclass(frozen=True)
class TimeRange:
    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class DialogueMessage:
    role: str
    content: str
    timestamp: str
    speaker_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureDialogue:
    messages: tuple[DialogueMessage, ...]
    occurred_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DialogueRecord:
    dialogue_id: str
    messages: tuple[DialogueMessage, ...]
    captured_at: str
    occurred_at: str
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retention_until: str | None = None
    redacted_at: str | None = None


@dataclass(frozen=True)
class DialogueRef:
    dialogue_id: str
    message_range: tuple[int, int] | None = None


@dataclass(frozen=True)
class MemoryUnit:
    unit_id: str
    scope: MemoryScope
    text: str
    memory_type: str
    timestamp: str
    available_at: str
    dialogue_refs: tuple[DialogueRef, ...] = ()
    confidence: float | None = None
    retention_until: str | None = None
    redacted_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureRequest:
    scope: MemoryScope
    dialogue: CaptureDialogue
    capture_time: str


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
class ExtractionRequest:
    scope: MemoryScope
    dialogue: DialogueRecord


@dataclass(frozen=True)
class ExtractionResult:
    units: tuple[MemoryUnit, ...]
    skipped: tuple[CaptureSkip, ...] = ()
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexSearchRequest:
    owner_id: str
    namespaces: tuple[str, ...] | None
    query: str
    time_range: TimeRange | None = None
    limit: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexHit:
    unit_id: str
    score: float
    retrieval_text: str
    score_breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryUnitSelector:
    owner_id: str | None = None
    namespaces: tuple[str, ...] | None = None
    unit_ids: tuple[str, ...] = ()
    time_range: TimeRange | None = None
    memory_types: tuple[str, ...] = ()
    include_redacted: bool = False
    limit: int | None = None
    order: Literal["newest_first", "oldest_first"] = "newest_first"


@dataclass(frozen=True)
class OperationLogSelector:
    owner_id: str | None = None
    namespaces: tuple[str, ...] | None = None
    operation_type: str | None = None
    status: str | None = None
    time_range: TimeRange | None = None
    limit: int | None = 20


@dataclass(frozen=True)
class OperationLogEntry:
    log_id: str
    operation_type: str
    created_at: str
    scope: MemoryScope | None
    status: str
    summary: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
