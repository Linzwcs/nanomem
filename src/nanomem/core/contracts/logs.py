"""Operation log entry shape.

Operation logs are a first-class audit/observability concept written by
the capture and read pipelines and surfaced by the control layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import MemoryScope


@dataclass(frozen=True)
class OperationLogEntry:
    log_id: str
    operation_type: str
    created_at: str
    scope: MemoryScope | None
    status: str
    summary: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)


__all__ = ["OperationLogEntry"]
