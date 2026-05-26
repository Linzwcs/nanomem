from __future__ import annotations

from typing import Protocol

from nanomem.core.contracts import ExtractionRequest, ExtractionResult


class MemoryUnitExtractor(Protocol):
    name: str

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        ...
