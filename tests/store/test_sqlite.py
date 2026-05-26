from __future__ import annotations

import json
import sqlite3

from nanomem.core.contracts import (
    DialogueMessage,
    Dialogue,
    DialogueRef,
    DialogueWindow,
    DialogueWindowSelector,
    MemoryScope,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    OperationLogSelector,
    Session,
)
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore


def test_sqlite_store_round_trips_dialogue_units_and_logs(tmp_path) -> None:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    try:
        dialogue = Dialogue(
            dialogue_id="dlg-1",
            session_id="session-1",
            messages=(
                DialogueMessage(
                    role="user",
                    speaker_id="user-1",
                    content="I prefer concise Chinese answers.",
                    timestamp="2026-01-05T00:00:00+00:00",
                ),
            ),
            started_at="2026-01-05T00:00:00+00:00",
            ended_at="2026-01-05T00:00:00+00:00",
            created_at="2026-01-05T00:00:01+00:00",
            updated_at="2026-01-05T00:00:01+00:00",
            checksum="checksum",
        )
        window = DialogueWindow(
            session_id="session-1",
            dialogue_id="dlg-1",
            status="open",
            token_count=8,
            message_count=1,
            created_at="2026-01-05T00:00:01+00:00",
            updated_at="2026-01-05T00:00:01+00:00",
        )
        store.put_session(
            Session(
                session_id="session-1",
                created_at="2026-01-05T00:00:01+00:00",
                updated_at="2026-01-05T00:00:01+00:00",
            )
        )
        store.put_dialogue(dialogue)
        store.put_dialogue_window(window)

        unit = MemoryUnit(
            unit_id="unit-1",
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            text="The user prefers concise Chinese answers.",
            memory_type="preference",
            timestamp="2026-01-05T00:00:00+00:00",
            available_at="2026-01-05T00:00:01+00:00",
            dialogue_refs=(DialogueRef(dialogue_id="dlg-1", message_range=(0, 1)),),
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
        assert store.query_dialogue_windows(
            DialogueWindowSelector(
                session_id="session-1",
                statuses=("open",),
            )
        ) == (window,)
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


def test_sqlite_store_counts_and_offsets_memory_units(tmp_path) -> None:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    try:
        units = tuple(
            MemoryUnit(
                unit_id=f"unit-{index}",
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                text=f"The user prefers option {index}.",
                memory_type="preference",
                timestamp=f"2026-01-0{index}T00:00:00+00:00",
                available_at=f"2026-01-0{index}T00:00:01+00:00",
            )
            for index in range(1, 4)
        )
        store.append_units(units)

        selector = MemoryUnitSelector(
            owner_id="user-1",
            namespaces=("personal",),
            text_query="option",
            limit=1,
            offset=1,
        )

        page = store.query_units(selector)

        assert store.count_units(selector) == 3
        assert len(page) == 1
        assert page[0].unit_id == "unit-2"
    finally:
        store.close()


def test_sqlite_migrates_legacy_dialogue_window_scope_columns(tmp_path) -> None:
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE dialogue_records (
              dialogue_id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              namespace TEXT NOT NULL,
              session_id TEXT,
              status TEXT NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              extracted_at TEXT,
              token_count INTEGER NOT NULL,
              checksum TEXT,
              messages_json TEXT NOT NULL,
              metadata_json TEXT NOT NULL,
              retention_until TEXT,
              redacted_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE dialogue_windows (
              dialogue_id TEXT PRIMARY KEY,
              owner_id TEXT NOT NULL,
              namespace TEXT NOT NULL,
              session_id TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              extracted_at TEXT,
              token_count INTEGER NOT NULL,
              metadata_json TEXT NOT NULL
            )
            """
        )
        message = {
            "role": "user",
            "content": "I prefer concise Chinese answers.",
            "timestamp": "2026-01-05T00:00:00+00:00",
        }
        connection.execute(
            """
            INSERT INTO dialogue_records (
              dialogue_id, owner_id, namespace, session_id, status, started_at,
              ended_at, created_at, updated_at, extracted_at, token_count,
              checksum, messages_json, metadata_json, retention_until, redacted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dlg-legacy",
                "user-1",
                "personal",
                "session-legacy",
                "open",
                "2026-01-05T00:00:00+00:00",
                "2026-01-05T00:00:00+00:00",
                "2026-01-05T00:00:01+00:00",
                "2026-01-05T00:00:01+00:00",
                None,
                8,
                "checksum",
                json.dumps([message]),
                "{}",
                None,
                None,
            ),
        )
        connection.execute(
            """
            INSERT INTO dialogue_windows (
              dialogue_id, owner_id, namespace, session_id, status, created_at,
              updated_at, extracted_at, token_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dlg-legacy",
                "user-1",
                "personal",
                "session-legacy",
                "open",
                "2026-01-05T00:00:01+00:00",
                "2026-01-05T00:00:01+00:00",
                None,
                8,
                "{}",
            ),
        )
        connection.execute("PRAGMA user_version = 5")
        connection.commit()
    finally:
        connection.close()

    store = SQLiteMemoryUnitStore(path)
    try:
        dialogue = store.get_dialogue("dlg-legacy")
        assert dialogue is not None
        assert dialogue.session_id == "session-legacy"
        assert not hasattr(dialogue, "scope")

        windows = store.query_dialogue_windows(
            DialogueWindowSelector(session_id="session-legacy")
        )
        assert len(windows) == 1
        assert windows[0].dialogue_id == "dlg-legacy"
        assert windows[0].message_count == 0
        assert not hasattr(windows[0], "scope")

        columns = {
            row["name"]
            for row in store._connection.execute(  # noqa: SLF001
                "PRAGMA table_info(dialogue_windows)"
            )
        }
        assert "owner_id" not in columns
        assert "namespace" not in columns
    finally:
        store.close()
