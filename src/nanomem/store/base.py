from __future__ import annotations

from typing import Protocol

from nanomem.contracts import (
    Dialogue,
    DialogueWindow,
    DialogueWindowSelector,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    OperationLogSelector,
    Session,
)


class MemoryStore(Protocol):
    def append_units(self, units: tuple[MemoryUnit, ...]) -> None:
        ...

    def get_units(self, unit_ids: tuple[str, ...]) -> tuple[MemoryUnit, ...]:
        ...

    def query_units(self, selector: MemoryUnitSelector) -> tuple[MemoryUnit, ...]:
        ...

    def put_session(self, session: Session) -> None:
        ...

    def get_session(self, session_id: str) -> Session | None:
        ...

    def put_dialogue(self, dialogue: Dialogue) -> None:
        ...

    def get_dialogue(self, dialogue_id: str) -> Dialogue | None:
        ...

    def put_dialogue_window(self, window: DialogueWindow) -> None:
        ...

    def query_dialogue_windows(
        self,
        selector: DialogueWindowSelector,
    ) -> tuple[DialogueWindow, ...]:
        ...

    def append_operation_log(self, entry: OperationLogEntry) -> None:
        ...

    def list_operation_logs(
        self,
        selector: OperationLogSelector,
    ) -> tuple[OperationLogEntry, ...]:
        ...
