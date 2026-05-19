from __future__ import annotations

from nanomem.contracts import (
    DialogueMessage,
    DialogueRecord,
    DialogueRef,
    MemoryScope,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    OperationLogSelector,
)
from nanomem.store.sqlite import SQLiteMemoryUnitStore


def test_sqlite_store_round_trips_dialogue_units_and_logs(tmp_path) -> None:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    try:
        dialogue = DialogueRecord(
            dialogue_id="dlg-1",
            messages=(
                DialogueMessage(
                    role="user",
                    speaker_id="user-1",
                    content="I prefer concise Chinese answers.",
                    timestamp="2026-01-05T00:00:00+00:00",
                ),
            ),
            occurred_at="2026-01-05T00:00:00+00:00",
            captured_at="2026-01-05T00:00:01+00:00",
            checksum="checksum",
        )
        store.put_dialogue(dialogue)

        unit = MemoryUnit(
            unit_id="unit-1",
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            text="The user prefers concise Chinese answers.",
            memory_type="preference",
            timestamp="2026-01-05T00:00:00+00:00",
            available_at="2026-01-05T00:00:01+00:00",
            dialogue_refs=(DialogueRef(dialogue_id="dlg-1", message_range=(0, 1)),),
            confidence=0.9,
        )
        store.append_units((unit,))

        store.append_operation_log(
            OperationLogEntry(
                log_id="log-1",
                operation_type="capture",
                created_at="2026-01-05T00:00:02+00:00",
                scope=MemoryScope(owner_id="user-1"),
                status="ok",
                summary={"unit_count": 1},
            )
        )

        assert store.get_dialogue("dlg-1") == dialogue
        assert store.get_units(("unit-1",)) == (unit,)
        assert store.query_units(
            MemoryUnitSelector(owner_id="user-1", namespaces=("personal",))
        ) == (unit,)

        logs = store.list_operation_logs(OperationLogSelector(owner_id="user-1"))
        assert len(logs) == 1
        assert logs[0].scope == MemoryScope(owner_id="user-1")

        stats = store.stats()
        assert stats["unit_count"] == 1
        assert stats["owner_count"] == 1
        assert stats["namespace_count"] == 1
        assert stats["dialogue_count"] == 1
        assert stats["operation_log_count"] == 1
    finally:
        store.close()
