from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nanomem.contracts import (
    MemoryScope,
    MemoryUnit,
    OperationLogEntry,
    OperationLogSelector,
    TimeRange,
)
from nanomem.index.base import MemoryUnitIndex
from nanomem.index.dense import DenseMemoryUnitIndex
from nanomem.store.sqlite import SQLiteMemoryUnitStore


@dataclass(frozen=True)
class DatabaseStats:
    store: str
    path: str
    file_size_bytes: int | None
    schema_version: int
    latest_schema_version: int
    unit_count: int
    owner_count: int
    namespace_count: int
    dialogue_count: int
    operation_log_count: int
    applied_schema_migration_count: int = 0
    pending_schema_migration_count: int = 0
    latest_operation_at: str | None = None
    oldest_timestamp: str | None = None
    newest_timestamp: str | None = None
    top_owners: tuple[dict[str, Any], ...] = ()
    index_backend: str | None = None
    index_document_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SchemaMigrationRecord:
    version: int
    name: str
    applied_at: str
    checksum: str


@dataclass(frozen=True)
class PendingSchemaMigration:
    version: int
    name: str


@dataclass(frozen=True)
class SchemaStatus:
    schema_version: int
    latest_schema_version: int
    needs_migration: bool
    applied: tuple[SchemaMigrationRecord, ...] = ()
    pending: tuple[PendingSchemaMigration, ...] = ()


@dataclass(frozen=True)
class ReindexResult:
    indexed_unit_count: int
    index_backend: str
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetentionPolicy:
    before: str
    scope: MemoryScope | None = None


@dataclass(frozen=True)
class RetentionPreview:
    policy: RetentionPolicy
    matched_unit_count: int
    oldest_timestamp: str | None = None
    newest_timestamp: str | None = None
    sample_units: tuple[MemoryUnit, ...] = ()


@dataclass(frozen=True)
class RetentionApplyResult:
    policy: RetentionPolicy
    deleted_unit_count: int
    reindex: ReindexResult


@dataclass(frozen=True)
class OperationLogRetentionPolicy:
    before: str
    scope: MemoryScope | None = None
    operation_type: str | None = None


@dataclass(frozen=True)
class OperationLogRetentionPreview:
    policy: OperationLogRetentionPolicy
    matched_log_count: int
    oldest_created_at: str | None = None
    newest_created_at: str | None = None
    sample_logs: tuple[OperationLogEntry, ...] = ()


@dataclass(frozen=True)
class OperationLogRetentionApplyResult:
    policy: OperationLogRetentionPolicy
    deleted_log_count: int


@dataclass(frozen=True)
class BackupResult:
    path: str
    file_size_bytes: int | None
    created_at: str


@dataclass(frozen=True)
class ExportResult:
    path: str
    file_size_bytes: int | None
    exported_at: str
    unit_count: int
    operation_log_count: int


@dataclass(frozen=True)
class IntegrityCheckResult:
    ok: bool
    messages: tuple[str, ...]


class NanoMemAdminService:
    """Control-plane operations for operators, CLI, and future TUI."""

    def __init__(
        self,
        *,
        store: SQLiteMemoryUnitStore,
        index: MemoryUnitIndex | None = None,
    ) -> None:
        self.store = store
        self.index = index or DenseMemoryUnitIndex()

    def stats(self) -> DatabaseStats:
        payload = self.store.stats()
        index_count = None
        if hasattr(self.index, "document_count"):
            index_count = int(self.index.document_count())  # type: ignore[attr-defined]
        return DatabaseStats(
            store=str(payload["store"]),
            path=str(payload["path"]),
            file_size_bytes=payload["file_size_bytes"],
            schema_version=int(payload["schema_version"]),
            latest_schema_version=int(payload["latest_schema_version"]),
            unit_count=int(payload["unit_count"]),
            owner_count=int(payload["owner_count"]),
            namespace_count=int(payload["namespace_count"]),
            dialogue_count=int(payload["dialogue_count"]),
            operation_log_count=int(payload["operation_log_count"]),
            applied_schema_migration_count=int(
                payload["applied_schema_migration_count"],
            ),
            pending_schema_migration_count=int(
                payload["pending_schema_migration_count"],
            ),
            latest_operation_at=payload.get("latest_operation_at"),
            oldest_timestamp=payload.get("oldest_timestamp"),
            newest_timestamp=payload.get("newest_timestamp"),
            top_owners=tuple(payload.get("top_owners", ())),
            index_backend=getattr(self.index, "name", type(self.index).__name__),
            index_document_count=index_count,
            metadata={
                "index": _index_metadata(self.index),
            },
        )

    def schema_status(self) -> SchemaStatus:
        payload = self.store.schema_status()
        return SchemaStatus(
            schema_version=int(payload["schema_version"]),
            latest_schema_version=int(payload["latest_schema_version"]),
            needs_migration=bool(payload["needs_migration"]),
            applied=tuple(
                SchemaMigrationRecord(
                    version=int(item["version"]),
                    name=str(item["name"]),
                    applied_at=str(item["applied_at"]),
                    checksum=str(item["checksum"]),
                )
                for item in payload.get("applied", ())
            ),
            pending=tuple(
                PendingSchemaMigration(
                    version=int(item["version"]),
                    name=str(item["name"]),
                )
                for item in payload.get("pending", ())
            ),
        )

    def integrity_check(self) -> IntegrityCheckResult:
        messages = self.store.integrity_check()
        return IntegrityCheckResult(
            ok=messages == ("ok",),
            messages=messages,
        )

    def backup(
        self,
        destination: str,
        *,
        overwrite: bool = False,
    ) -> BackupResult:
        payload = self.store.backup_to(destination, overwrite=overwrite)
        return BackupResult(
            path=str(payload["path"]),
            file_size_bytes=payload["file_size_bytes"],
            created_at=str(payload["created_at"]),
        )

    def export_json(
        self,
        destination: str,
        *,
        include_operation_logs: bool = True,
        overwrite: bool = False,
    ) -> ExportResult:
        payload = self.store.export_json(
            destination,
            include_operation_logs=include_operation_logs,
            overwrite=overwrite,
        )
        return ExportResult(
            path=str(payload["path"]),
            file_size_bytes=payload["file_size_bytes"],
            exported_at=str(payload["exported_at"]),
            unit_count=int(payload["unit_count"]),
            operation_log_count=int(payload["operation_log_count"]),
        )

    def list_units(
        self,
        *,
        scope: MemoryScope | None = None,
        time_range: TimeRange | None = None,
        limit: int | None = 20,
    ) -> tuple[MemoryUnit, ...]:
        return self.store.list_units(
            scope=scope,
            time_range=time_range,
            limit=limit,
        )

    def list_operation_logs(
        self,
        *,
        scope: MemoryScope | None = None,
        operation_type: str | None = None,
        limit: int | None = 20,
    ) -> tuple[OperationLogEntry, ...]:
        return self.store.list_operation_logs(
            OperationLogSelector(
                owner_id=scope.owner_id if scope else None,
                namespaces=(scope.namespace,) if scope and scope.namespace else None,
                operation_type=operation_type,
                limit=limit,
            )
        )

    def reindex(
        self,
        *,
        scope: MemoryScope | None = None,
        time_range: TimeRange | None = None,
    ) -> ReindexResult:
        units = self.store.list_units(
            scope=scope,
            time_range=time_range,
            limit=None,
        )
        self.index.clear()
        self.index.upsert(units)
        return ReindexResult(
            indexed_unit_count=len(units),
            index_backend=getattr(self.index, "name", type(self.index).__name__),
            stats={
                "scope_filtered": scope is not None,
                "time_range_filtered": time_range is not None,
            },
        )

    def retention_preview(
        self,
        policy: RetentionPolicy,
        *,
        sample_limit: int = 10,
    ) -> RetentionPreview:
        units = _expired_units(
            self.store.list_units(
                scope=policy.scope,
                limit=None,
            ),
            before=policy.before,
        )
        sample = tuple(units[:sample_limit])
        timestamps = [
            unit.timestamp or unit.available_at
            for unit in units
        ]
        return RetentionPreview(
            policy=policy,
            matched_unit_count=len(units),
            oldest_timestamp=min(timestamps) if timestamps else None,
            newest_timestamp=max(timestamps) if timestamps else None,
            sample_units=sample,
        )

    def retention_apply(self, policy: RetentionPolicy) -> RetentionApplyResult:
        deleted = self.store.delete_units_before(
            cutoff=policy.before,
            scope=policy.scope,
        )
        reindex = self.reindex()
        return RetentionApplyResult(
            policy=policy,
            deleted_unit_count=deleted,
            reindex=reindex,
        )

    def operation_log_retention_preview(
        self,
        policy: OperationLogRetentionPolicy,
        *,
        sample_limit: int = 10,
    ) -> OperationLogRetentionPreview:
        logs = _expired_operation_logs(
            self.store.list_operation_logs(
                OperationLogSelector(
                    owner_id=policy.scope.owner_id if policy.scope else None,
                    namespaces=(
                        (policy.scope.namespace,)
                        if policy.scope and policy.scope.namespace
                        else None
                    ),
                    operation_type=policy.operation_type,
                    limit=None,
                )
            ),
            before=policy.before,
        )
        sample = tuple(logs[:sample_limit])
        timestamps = [log.created_at for log in logs]
        return OperationLogRetentionPreview(
            policy=policy,
            matched_log_count=len(logs),
            oldest_created_at=min(timestamps) if timestamps else None,
            newest_created_at=max(timestamps) if timestamps else None,
            sample_logs=sample,
        )

    def operation_log_retention_apply(
        self,
        policy: OperationLogRetentionPolicy,
    ) -> OperationLogRetentionApplyResult:
        deleted = self.store.delete_operation_logs_before(
            cutoff=policy.before,
            scope=policy.scope,
            operation_type=policy.operation_type,
        )
        return OperationLogRetentionApplyResult(
            policy=policy,
            deleted_log_count=deleted,
        )


def _expired_units(
    units: tuple[MemoryUnit, ...],
    *,
    before: str,
) -> tuple[MemoryUnit, ...]:
    return tuple(
        unit for unit in units
        if (unit.timestamp or unit.available_at) < before
    )


def _expired_operation_logs(
    logs: tuple[OperationLogEntry, ...],
    *,
    before: str,
) -> tuple[OperationLogEntry, ...]:
    return tuple(log for log in logs if log.created_at < before)


def _index_metadata(index: MemoryUnitIndex) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "backend": getattr(index, "name", type(index).__name__),
    }
    embedding_model = getattr(index, "embedding_model", None)
    if embedding_model is not None:
        payload["embedding_model"] = getattr(
            embedding_model,
            "name",
            type(embedding_model).__name__,
        )
    if hasattr(index, "stats"):
        payload["stats"] = index.stats()  # type: ignore[attr-defined]
    dense = getattr(index, "dense", None)
    if dense is not None:
        payload["dense"] = _index_metadata(dense)
    lexical = getattr(index, "lexical", None)
    if lexical is not None:
        payload["lexical"] = _index_metadata(lexical)
    return payload
