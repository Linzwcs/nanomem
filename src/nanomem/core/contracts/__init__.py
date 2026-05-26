"""Public data contracts for the nanomem package.

This package re-exports every public name from the split sub-modules so
``from nanomem.core.contracts import X`` works for any of them:

- :mod:`nanomem.core.contracts.core` — domain entities (Session,
  Dialogue, MemoryUnit, MemoryScope, ...)
- :mod:`nanomem.core.contracts.requests` — request payloads
  (CaptureRequest, ReadRequest, FlushRequest, ...)
- :mod:`nanomem.core.contracts.results` — result and retrieval payloads
  (CaptureResult, ReadResult, RankedMemoryUnit, PackedContext, ...)
- :mod:`nanomem.core.contracts.selectors` — query filters
- :mod:`nanomem.core.contracts.logs` — :class:`OperationLogEntry`

The flat top-level ``from nanomem import X`` form (re-exported from
:mod:`nanomem.__init__`) also remains the most convenient public surface.
"""

from __future__ import annotations

from .core import (
    CaptureDialogue,
    Dialogue,
    DialogueMessage,
    DialogueRef,
    DialogueStatus,
    DialogueWindow,
    MemoryScope,
    MemoryUnit,
    Session,
    TimeRange,
)
from .logs import OperationLogEntry
from .requests import (
    CaptureRequest,
    ExtractionRequest,
    FlushRequest,
    IndexSearchRequest,
    ReadRequest,
)
from .results import (
    CaptureResult,
    CaptureSkip,
    ExtractionResult,
    FlushResult,
    IndexHit,
    PackedContext,
    RankedMemoryUnit,
    ReadResult,
    ReindexResult,
)
from .selectors import (
    DialogueWindowSelector,
    MemoryUnitSelector,
    OperationLogSelector,
)


__all__ = [
    "CaptureDialogue",
    "CaptureRequest",
    "CaptureResult",
    "CaptureSkip",
    "Dialogue",
    "DialogueMessage",
    "DialogueRef",
    "DialogueStatus",
    "DialogueWindow",
    "DialogueWindowSelector",
    "ExtractionRequest",
    "ExtractionResult",
    "FlushRequest",
    "FlushResult",
    "IndexHit",
    "IndexSearchRequest",
    "MemoryScope",
    "MemoryUnit",
    "MemoryUnitSelector",
    "OperationLogEntry",
    "OperationLogSelector",
    "PackedContext",
    "RankedMemoryUnit",
    "ReadRequest",
    "ReadResult",
    "ReindexResult",
    "Session",
    "TimeRange",
]
