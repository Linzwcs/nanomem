from __future__ import annotations

from typing import Protocol

from nanomem.contracts import (
    DialogueRecord,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    OperationLogSelector,
)


class MemoryStore(Protocol):
    def append_units(self, units: tuple[MemoryUnit, ...]) -> None:
        ...

    def get_units(self, unit_ids: tuple[str, ...]) -> tuple[MemoryUnit, ...]:
        ...

    def query_units(self, selector: MemoryUnitSelector) -> tuple[MemoryUnit, ...]:
        ...

    def put_dialogue(self, record: DialogueRecord) -> None:
        ...

    def get_dialogue(self, dialogue_id: str) -> DialogueRecord | None:
        ...

    def append_operation_log(self, entry: OperationLogEntry) -> None:
        ...

    def list_operation_logs(
        self,
        selector: OperationLogSelector,
    ) -> tuple[OperationLogEntry, ...]:
        ...
