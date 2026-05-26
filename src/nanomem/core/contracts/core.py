"""Core domain entities and shared primitives.

This module hosts the long-lived data shapes that the rest of the
package builds on:

- :class:`MemoryScope`, :class:`TimeRange` — shared primitives;
- :class:`DialogueMessage`, :class:`Dialogue`, :class:`DialogueWindow`,
  :class:`DialogueRef` — capture-side dialogue model;
- :class:`Session` — session-level metadata;
- :class:`MemoryUnit` — the durable storage unit;
- :class:`CaptureDialogue` — the input payload used by capture requests.

All types are frozen dataclasses; treat them as immutable values.
"""

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


DialogueStatus = Literal["open", "sealed", "extracting", "extracted", "failed"]


@dataclass(frozen=True)
class Session:
    session_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Dialogue:
    dialogue_id: str
    session_id: str | None
    messages: tuple[DialogueMessage, ...]
    started_at: str
    ended_at: str
    created_at: str
    updated_at: str
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retention_until: str | None = None
    redacted_at: str | None = None


@dataclass(frozen=True)
class DialogueWindow:
    session_id: str
    dialogue_id: str
    status: DialogueStatus
    token_count: int
    message_count: int
    created_at: str
    updated_at: str
    sealed_at: str | None = None
    extracted_at: str | None = None
    seal_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


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
    retention_until: str | None = None
    redacted_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "CaptureDialogue",
    "Dialogue",
    "DialogueMessage",
    "DialogueRef",
    "DialogueStatus",
    "DialogueWindow",
    "MemoryScope",
    "MemoryUnit",
    "Session",
    "TimeRange",
]
