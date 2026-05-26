"""Selectors for store and operation-log queries.

A selector is a frozen filter used by the store / control layer to scope
``list_*`` queries. Selectors do not own scope by themselves — pair with
:class:`~nanomem.contracts.core.MemoryScope` semantics at the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanomem.contracts.core import DialogueStatus, TimeRange


@dataclass(frozen=True)
class MemoryUnitSelector:
    owner_id: str | None = None
    namespaces: tuple[str, ...] | None = None
    unit_ids: tuple[str, ...] = ()
    time_range: TimeRange | None = None
    memory_types: tuple[str, ...] = ()
    text_query: str | None = None
    include_redacted: bool = False
    limit: int | None = None
    offset: int = 0
    order: Literal["newest_first", "oldest_first"] = "newest_first"


@dataclass(frozen=True)
class DialogueWindowSelector:
    session_id: str | None = None
    statuses: tuple[DialogueStatus, ...] = ()
    dialogue_ids: tuple[str, ...] = ()
    include_redacted: bool = False
    limit: int | None = None
    offset: int = 0
    order: Literal["newest_first", "oldest_first"] = "newest_first"


@dataclass(frozen=True)
class OperationLogSelector:
    owner_id: str | None = None
    namespaces: tuple[str, ...] | None = None
    operation_type: str | None = None
    status: str | None = None
    time_range: TimeRange | None = None
    limit: int | None = 20


__all__ = [
    "DialogueWindowSelector",
    "MemoryUnitSelector",
    "OperationLogSelector",
]
