from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any

from nanomem.contracts import (
    DialogueMessage,
    DialogueRecord,
    DialogueRef,
    MemoryScope,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    OperationLogSelector,
    TimeRange,
)
from nanomem.time import now_utc_iso


SCHEMA_VERSION = 3
MIGRATIONS: tuple[tuple[int, str], ...] = (
    (1, "legacy_initial_schema"),
    (2, "legacy_scope_indexes"),
    (3, "dialogue_centered_memory_store"),
)


class SQLiteMemoryUnitStore:
    """SQLite-backed authoritative store for MemoryUnits and DialogueRecords."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._init_schema()

    def append_units(self, units: tuple[MemoryUnit, ...]) -> None:
        with self._lock:
            with self._connection:
                self._connection.executemany(
                    """
                    INSERT OR IGNORE INTO memory_units (
                      unit_id, owner_id, namespace, text, memory_type,
                      timestamp, available_at, dialogue_refs_json,
                      retention_until, redacted_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(_unit_row(unit) for unit in units),
                )

    def get_units(self, unit_ids: tuple[str, ...]) -> tuple[MemoryUnit, ...]:
        if not unit_ids:
            return ()
        placeholders = ", ".join("?" for _ in unit_ids)
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT * FROM memory_units
                WHERE unit_id IN ({placeholders})
                """,
                unit_ids,
            ).fetchall()
        by_id = {row["unit_id"]: _row_to_unit(row) for row in rows}
        return tuple(by_id[unit_id] for unit_id in unit_ids if unit_id in by_id)

    def query_units(self, selector: MemoryUnitSelector) -> tuple[MemoryUnit, ...]:
        query, params = _query_units_sql(selector, count=False)
        with self._lock:
            rows = self._connection.execute(query, tuple(params)).fetchall()
        return tuple(_row_to_unit(row) for row in rows)

    def count_units(self, selector: MemoryUnitSelector) -> int:
        query, params = _query_units_sql(selector, count=True)
        with self._lock:
            row = self._connection.execute(query, tuple(params)).fetchone()
        return int(row[0]) if row is not None else 0

    def put_dialogue(self, record: DialogueRecord) -> None:
        with self._lock:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT OR REPLACE INTO dialogue_records (
                      dialogue_id, occurred_at, captured_at, checksum,
                      messages_json, metadata_json, retention_until, redacted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.dialogue_id,
                        record.occurred_at,
                        record.captured_at,
                        record.checksum,
                        _json([asdict(message) for message in record.messages]),
                        _json(record.metadata),
                        record.retention_until,
                        record.redacted_at,
                    ),
                )

    def get_dialogue(self, dialogue_id: str) -> DialogueRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM dialogue_records WHERE dialogue_id = ?",
                (dialogue_id,),
            ).fetchone()
        return None if row is None else _row_to_dialogue(row)

    def append_operation_log(self, entry: OperationLogEntry) -> None:
        scope = entry.scope
        with self._lock:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO operation_logs (
                      log_id, created_at, operation_type, owner_id, namespace,
                      status, summary_json, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.log_id,
                        entry.created_at,
                        entry.operation_type,
                        scope.owner_id if scope else None,
                        scope.namespace if scope else None,
                        entry.status,
                        _json(entry.summary),
                        _json(entry.payload),
                    ),
                )

    def list_operation_logs(
        self,
        selector: OperationLogSelector,
    ) -> tuple[OperationLogEntry, ...]:
        clauses: list[str] = []
        params: list[object] = []
        if selector.owner_id is not None:
            clauses.append("owner_id = ?")
            params.append(selector.owner_id)
        if selector.namespaces is not None:
            if not selector.namespaces:
                return ()
            clauses.append(
                "namespace IN (" + ", ".join("?" for _ in selector.namespaces) + ")"
            )
            params.extend(selector.namespaces)
        if selector.operation_type is not None:
            clauses.append("operation_type = ?")
            params.append(selector.operation_type)
        if selector.status is not None:
            clauses.append("status = ?")
            params.append(selector.status)
        if selector.time_range is not None:
            if selector.time_range.start is not None:
                clauses.append("created_at >= ?")
                params.append(selector.time_range.start)
            if selector.time_range.end is not None:
                clauses.append("created_at <= ?")
                params.append(selector.time_range.end)

        query = "SELECT * FROM operation_logs"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, log_id DESC"
        if selector.limit is not None:
            query += " LIMIT ?"
            params.append(selector.limit)
        with self._lock:
            rows = self._connection.execute(query, tuple(params)).fetchall()
        return tuple(_row_to_operation_log(row) for row in rows)

    # Control-plane helpers used by CLI and manager. They are intentionally outside
    # the MemoryStore protocol.
    def list_units(
        self,
        *,
        scope: MemoryScope | None = None,
        time_range: TimeRange | None = None,
        limit: int | None = None,
    ) -> tuple[MemoryUnit, ...]:
        return self.query_units(
            MemoryUnitSelector(
                owner_id=scope.owner_id if scope else None,
                namespaces=(scope.namespace,) if scope and scope.namespace else None,
                time_range=time_range,
                limit=limit,
            )
        )

    def stats(self) -> dict[str, Any]:
        with self._lock:
            schema_version = _schema_version(self._connection)
            migrations = _schema_migration_records(self._connection)
            unit_count = _scalar(self._connection, "SELECT COUNT(*) FROM memory_units")
            active_unit_count = _scalar(
                self._connection,
                "SELECT COUNT(*) FROM memory_units WHERE redacted_at IS NULL",
            )
            owner_count = _scalar(
                self._connection,
                "SELECT COUNT(DISTINCT owner_id) FROM memory_units",
            )
            namespace_count = _scalar(
                self._connection,
                "SELECT COUNT(DISTINCT namespace) FROM memory_units",
            )
            dialogue_count = _scalar(
                self._connection,
                "SELECT COUNT(*) FROM dialogue_records",
            )
            operation_log_count = _scalar(
                self._connection,
                "SELECT COUNT(*) FROM operation_logs",
            )
            latest_operation = self._connection.execute(
                "SELECT MAX(created_at) AS latest_at FROM operation_logs"
            ).fetchone()
            bounds = self._connection.execute(
                """
                SELECT MIN(timestamp) AS oldest_at, MAX(timestamp) AS newest_at
                FROM memory_units
                """
            ).fetchone()
            top_owners = self._connection.execute(
                """
                SELECT owner_id, namespace, COUNT(*) AS unit_count
                FROM memory_units
                GROUP BY owner_id, namespace
                ORDER BY unit_count DESC, owner_id ASC
                LIMIT 10
                """
            ).fetchall()
        migration_versions = {int(item["version"]) for item in migrations}
        return {
            "store": "sqlite",
            "path": self.path,
            "file_size_bytes": _file_size(self.path),
            "schema_version": schema_version,
            "latest_schema_version": SCHEMA_VERSION,
            "applied_schema_migration_count": len(migrations),
            "pending_schema_migration_count": len(
                [
                    version
                    for version, _ in MIGRATIONS
                    if version not in migration_versions
                ]
            ),
            "unit_count": unit_count,
            "active_unit_count": active_unit_count,
            "owner_count": owner_count,
            "namespace_count": namespace_count,
            "dialogue_count": dialogue_count,
            "operation_log_count": operation_log_count,
            "latest_operation_at": (
                latest_operation["latest_at"] if latest_operation else None
            ),
            "oldest_timestamp": bounds["oldest_at"] if bounds else None,
            "newest_timestamp": bounds["newest_at"] if bounds else None,
            "top_owners": [
                {
                    "owner_id": row["owner_id"],
                    "namespace": row["namespace"],
                    "unit_count": row["unit_count"],
                }
                for row in top_owners
            ],
        }

    def schema_status(self) -> dict[str, Any]:
        with self._lock:
            schema_version = _schema_version(self._connection)
            applied = _schema_migration_records(self._connection)
        applied_versions = {int(item["version"]) for item in applied}
        pending = [
            {"version": version, "name": name}
            for version, name in MIGRATIONS
            if version not in applied_versions
        ]
        return {
            "schema_version": schema_version,
            "latest_schema_version": SCHEMA_VERSION,
            "needs_migration": bool(pending),
            "applied": applied,
            "pending": pending,
        }

    def integrity_check(self) -> tuple[str, ...]:
        with self._lock:
            rows = self._connection.execute("PRAGMA integrity_check").fetchall()
        return tuple(str(row[0]) for row in rows)

    def backup_to(
        self,
        destination: str | Path,
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        path = Path(destination)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Backup destination already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            target = sqlite3.connect(str(path))
            try:
                self._connection.backup(target)
            finally:
                target.close()
        return {
            "path": str(path),
            "file_size_bytes": _file_size(str(path)),
            "created_at": now_utc_iso(),
        }

    def export_json(
        self,
        destination: str | Path,
        *,
        include_operation_logs: bool = True,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        path = Path(destination)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Export destination already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        units = self.list_units(limit=None)
        logs = (
            self.list_operation_logs(OperationLogSelector(limit=None))
            if include_operation_logs
            else ()
        )
        exported_at = now_utc_iso()
        payload = {
            "exported_at": exported_at,
            "schema": self.schema_status(),
            "stats": self.stats(),
            "units": [asdict(unit) for unit in units],
            "operation_logs": [asdict(log) for log in logs],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        return {
            "path": str(path),
            "file_size_bytes": _file_size(str(path)),
            "exported_at": exported_at,
            "unit_count": len(units),
            "operation_log_count": len(logs),
        }

    def delete_units_before(
        self,
        *,
        cutoff: str,
        scope: MemoryScope | None = None,
    ) -> int:
        selector = MemoryUnitSelector(
            owner_id=scope.owner_id if scope else None,
            namespaces=(scope.namespace,) if scope and scope.namespace else None,
            time_range=TimeRange(end=cutoff),
            include_redacted=True,
            limit=None,
        )
        unit_ids = tuple(unit.unit_id for unit in self.query_units(selector))
        if not unit_ids:
            return 0
        placeholders = ", ".join("?" for _ in unit_ids)
        with self._lock:
            with self._connection:
                cursor = self._connection.execute(
                    f"DELETE FROM memory_units WHERE unit_id IN ({placeholders})",
                    unit_ids,
                )
        return int(cursor.rowcount or 0)

    def delete_operation_logs_before(
        self,
        *,
        cutoff: str,
        scope: MemoryScope | None = None,
        operation_type: str | None = None,
    ) -> int:
        selector = OperationLogSelector(
            owner_id=scope.owner_id if scope else None,
            namespaces=(scope.namespace,) if scope and scope.namespace else None,
            operation_type=operation_type,
            time_range=TimeRange(end=cutoff),
            limit=None,
        )
        log_ids = tuple(log.log_id for log in self.list_operation_logs(selector))
        if not log_ids:
            return 0
        placeholders = ", ".join("?" for _ in log_ids)
        with self._lock:
            with self._connection:
                cursor = self._connection.execute(
                    f"DELETE FROM operation_logs WHERE log_id IN ({placeholders})",
                    log_ids,
                )
        return int(cursor.rowcount or 0)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _init_schema(self) -> None:
        with self._lock:
            with self._connection:
                current_version = _schema_version(self._connection)
                if current_version > SCHEMA_VERSION:
                    raise RuntimeError(
                        "NanoMem database schema is newer than this code: "
                        f"{current_version} > {SCHEMA_VERSION}"
                    )
                _apply_schema(self._connection)
                self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                for version, name in MIGRATIONS:
                    _record_migration(self._connection, version, name)


def _apply_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS memory_units (
          unit_id TEXT PRIMARY KEY,
          owner_id TEXT NOT NULL,
          namespace TEXT NOT NULL,
          text TEXT NOT NULL,
          memory_type TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          available_at TEXT NOT NULL,
          dialogue_refs_json TEXT NOT NULL,
          retention_until TEXT,
          redacted_at TEXT,
          metadata_json TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS memory_units_scope_time_idx
        ON memory_units (
          owner_id, namespace, timestamp, available_at
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS memory_units_type_time_idx
        ON memory_units (
          owner_id, namespace, memory_type, timestamp
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS dialogue_records (
          dialogue_id TEXT PRIMARY KEY,
          occurred_at TEXT NOT NULL,
          captured_at TEXT NOT NULL,
          checksum TEXT,
          messages_json TEXT NOT NULL,
          metadata_json TEXT NOT NULL,
          retention_until TEXT,
          redacted_at TEXT
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS dialogue_records_time_idx
        ON dialogue_records (occurred_at, captured_at)
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS operation_logs (
          log_id TEXT PRIMARY KEY,
          created_at TEXT NOT NULL,
          operation_type TEXT NOT NULL,
          owner_id TEXT,
          namespace TEXT,
          status TEXT NOT NULL,
          summary_json TEXT NOT NULL,
          payload_json TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS operation_logs_scope_idx
        ON operation_logs (
          owner_id, namespace, operation_type, status, created_at
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          applied_at TEXT NOT NULL,
          checksum TEXT NOT NULL
        )
    """)


def _record_migration(
    connection: sqlite3.Connection,
    version: int,
    name: str,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO schema_migrations
        (version, name, applied_at, checksum)
        VALUES (?, ?, ?, ?)
        """,
        (version, name, now_utc_iso(), f"{version}:{name}"),
    )


def _schema_migration_records(
    connection: sqlite3.Connection,
) -> tuple[dict[str, Any], ...]:
    rows = connection.execute(
        """
        SELECT version, name, applied_at, checksum
        FROM schema_migrations
        ORDER BY version ASC
        """
    ).fetchall()
    return tuple(
        {
            "version": int(row["version"]),
            "name": row["name"],
            "applied_at": row["applied_at"],
            "checksum": row["checksum"],
        }
        for row in rows
    )


def _query_units_sql(
    selector: MemoryUnitSelector,
    *,
    count: bool,
) -> tuple[str, list[object]]:
    if selector.offset < 0:
        raise ValueError("MemoryUnitSelector.offset must be non-negative")
    if selector.limit is not None and selector.limit < 0:
        raise ValueError("MemoryUnitSelector.limit must be non-negative")
    clauses: list[str] = []
    params: list[object] = []
    if selector.owner_id is not None:
        clauses.append("owner_id = ?")
        params.append(selector.owner_id)
    if selector.namespaces is not None:
        if not selector.namespaces:
            clauses.append("0")
        else:
            clauses.append(
                "namespace IN (" + ", ".join("?" for _ in selector.namespaces) + ")"
            )
            params.extend(selector.namespaces)
    if selector.unit_ids:
        clauses.append(
            "unit_id IN (" + ", ".join("?" for _ in selector.unit_ids) + ")"
        )
        params.extend(selector.unit_ids)
    if selector.memory_types:
        clauses.append(
            "memory_type IN ("
            + ", ".join("?" for _ in selector.memory_types)
            + ")"
        )
        params.extend(selector.memory_types)
    if selector.text_query is not None:
        text = selector.text_query.strip()
        if text:
            clauses.append("LOWER(text) LIKE ?")
            params.append(f"%{text.lower()}%")
    if selector.time_range is not None:
        if selector.time_range.start is not None:
            clauses.append("timestamp >= ?")
            params.append(selector.time_range.start)
        if selector.time_range.end is not None:
            clauses.append("timestamp <= ?")
            params.append(selector.time_range.end)
    if not selector.include_redacted:
        clauses.append("redacted_at IS NULL")

    query = "SELECT COUNT(*) FROM memory_units" if count else "SELECT * FROM memory_units"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    if count:
        return query, params
    direction = "ASC" if selector.order == "oldest_first" else "DESC"
    query += f" ORDER BY timestamp {direction}, unit_id ASC"
    if selector.limit is not None:
        query += " LIMIT ?"
        params.append(selector.limit)
    elif selector.offset:
        query += " LIMIT -1"
    if selector.offset:
        query += " OFFSET ?"
        params.append(selector.offset)
    return query, params


def _unit_row(unit: MemoryUnit) -> tuple[Any, ...]:
    namespace = unit.scope.namespace
    if namespace is None:
        raise ValueError("Stored MemoryUnit namespace must be resolved")
    return (
        unit.unit_id,
        unit.scope.owner_id,
        namespace,
        unit.text,
        unit.memory_type,
        unit.timestamp,
        unit.available_at,
        _json([asdict(ref) for ref in unit.dialogue_refs]),
        unit.retention_until,
        unit.redacted_at,
        _json(unit.metadata),
    )


def _row_to_unit(row: sqlite3.Row) -> MemoryUnit:
    return MemoryUnit(
        unit_id=row["unit_id"],
        scope=MemoryScope(
            owner_id=row["owner_id"],
            namespace=row["namespace"],
        ),
        text=row["text"],
        memory_type=row["memory_type"],
        timestamp=row["timestamp"],
        available_at=row["available_at"],
        dialogue_refs=_dialogue_refs_from_json(row["dialogue_refs_json"]),
        retention_until=row["retention_until"],
        redacted_at=row["redacted_at"],
        metadata=_load_json(row["metadata_json"]),
    )


def _row_to_dialogue(row: sqlite3.Row) -> DialogueRecord:
    return DialogueRecord(
        dialogue_id=row["dialogue_id"],
        occurred_at=row["occurred_at"],
        captured_at=row["captured_at"],
        checksum=row["checksum"],
        messages=_messages_from_json(row["messages_json"]),
        metadata=_load_json(row["metadata_json"]),
        retention_until=row["retention_until"],
        redacted_at=row["redacted_at"],
    )


def _row_to_operation_log(row: sqlite3.Row) -> OperationLogEntry:
    owner_id = row["owner_id"]
    namespace = row["namespace"]
    return OperationLogEntry(
        log_id=row["log_id"],
        operation_type=row["operation_type"],
        created_at=row["created_at"],
        scope=(
            MemoryScope(owner_id=owner_id, namespace=namespace)
            if owner_id
            else None
        ),
        status=row["status"],
        summary=_load_json(row["summary_json"]),
        payload=_load_json(row["payload_json"]),
    )


def _messages_from_json(payload: str | None) -> tuple[DialogueMessage, ...]:
    value = _load_json_list(payload)
    messages = []
    for item in value:
        if isinstance(item, dict):
            messages.append(
                DialogueMessage(
                    role=str(item.get("role", "")),
                    content=str(item.get("content", "")),
                    timestamp=str(item.get("timestamp", "")),
                    speaker_id=_optional_str(item.get("speaker_id")),
                    metadata=_mapping(item.get("metadata")),
                )
            )
    return tuple(messages)


def _dialogue_refs_from_json(payload: str | None) -> tuple[DialogueRef, ...]:
    value = _load_json_list(payload)
    refs = []
    for item in value:
        if not isinstance(item, dict):
            continue
        message_range = item.get("message_range")
        refs.append(
            DialogueRef(
                dialogue_id=str(item.get("dialogue_id", "")),
                message_range=(
                    None
                    if message_range is None
                    else (int(message_range[0]), int(message_range[1]))
                ),
            )
        )
    return tuple(refs)


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _load_json(payload: str | None) -> dict[str, Any]:
    if not payload:
        return {}
    value = json.loads(payload)
    if isinstance(value, dict):
        return value
    return {"value": value}


def _load_json_list(payload: str | None) -> list[Any]:
    if not payload:
        return []
    value = json.loads(payload)
    return value if isinstance(value, list) else []


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _scalar(connection: sqlite3.Connection, query: str) -> int:
    value = connection.execute(query).fetchone()[0]
    return int(value or 0)


def _schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0] or 0)


def _file_size(path: str) -> int | None:
    if path == ":memory:":
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    return file_path.stat().st_size
