from __future__ import annotations

from typing import Protocol

from nanomem.core.contracts import IndexHit, IndexSearchRequest, MemoryUnit


class MemoryUnitIndex(Protocol):
    def clear(self) -> None:
        ...

    def upsert(self, units: tuple[MemoryUnit, ...]) -> None:
        ...

    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]:
        ...

    def delete(self, unit_ids: tuple[str, ...]) -> None:
        ...
