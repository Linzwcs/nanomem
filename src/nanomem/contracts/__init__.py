"""Public data contracts for the nanomem package.

This package preserves the historical ``from nanomem.contracts import X``
surface by re-exporting every public name from the split sub-modules:

- :mod:`nanomem.contracts.core` — domain entities (Session, Dialogue,
  MemoryUnit, MemoryScope, ...)
- :mod:`nanomem.contracts.requests` — request payloads
  (CaptureRequest, ReadRequest, FlushRequest, ...)
- :mod:`nanomem.contracts.results` — result and retrieval payloads
  (CaptureResult, ReadResult, RankedMemoryUnit, PackedContext, ...)
- :mod:`nanomem.contracts.selectors` — query filters
- :mod:`nanomem.contracts.logs` — :class:`OperationLogEntry`

New code may import from the sub-modules directly. Existing code that
imports from :mod:`nanomem.contracts` continues to work unchanged.
"""

from __future__ import annotations

from nanomem.contracts.core import (
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
from nanomem.contracts.logs import OperationLogEntry
from nanomem.contracts.requests import (
    CaptureRequest,
    ExtractionRequest,
    FlushRequest,
    IndexSearchRequest,
    ReadRequest,
)
from nanomem.contracts.results import (
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
from nanomem.contracts.selectors import (
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
