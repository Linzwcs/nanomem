from __future__ import annotations

from typing import Any

from nanomem.core.contracts import (
    MemoryScope,
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogEntry,
    OperationLogSelector,
    ReindexResult,
    TimeRange,
)
from nanomem.control.types import (
    BackupResult,
    DatabaseStats,
    ExportResult,
    IntegrityCheckResult,
    OperationLogRetentionApplyResult,
    OperationLogRetentionPolicy,
    OperationLogRetentionPreview,
    PendingSchemaMigration,
    RetentionApplyResult,
    RetentionPolicy,
    RetentionPreview,
    SchemaMigrationRecord,
    SchemaStatus,
)
from nanomem.pipeline.retrieval.indexes.base import MemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.pipeline.retrieval.indexes.rebuild import rebuild_index
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore


class NanoMemControlService:
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
        active_unit_count = int(payload["active_unit_count"])
        last_reindex = self.store.list_operation_logs(
            OperationLogSelector(
                operation_type="reindex",
                status="ok",
                limit=1,
            )
        )
        return DatabaseStats(
            store=str(payload["store"]),
            path=str(payload["path"]),
            file_size_bytes=payload["file_size_bytes"],
            schema_version=int(payload["schema_version"]),
            latest_schema_version=int(payload["latest_schema_version"]),
            unit_count=int(payload["unit_count"]),
            active_unit_count=active_unit_count,
            owner_count=int(payload["owner_count"]),
            namespace_count=int(payload["namespace_count"]),
            session_count=int(payload.get("session_count", 0)),
            dialogue_count=int(payload["dialogue_count"]),
            dialogue_window_count=int(payload.get("dialogue_window_count", 0)),
            open_dialogue_window_count=int(
                payload.get("open_dialogue_window_count", 0)
            ),
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
            index_health=_index_health(active_unit_count, index_count),
            index_unit_delta=(
                None if index_count is None else active_unit_count - index_count
            ),
            last_reindex_at=last_reindex[0].created_at if last_reindex else None,
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
        return rebuild_index(
            store=self.store,
            index=self.index,
            selector=MemoryUnitSelector(
                owner_id=scope.owner_id if scope else None,
                namespaces=(
                    (scope.namespace,)
                    if scope and scope.namespace is not None
                    else None
                ),
                time_range=time_range,
                limit=None,
            ),
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


def _index_health(active_unit_count: int, index_count: int | None) -> str:
    if index_count is None:
        return "unknown"
    if index_count == active_unit_count:
        return "synced"
    return "stale"


# Backward-compatible public name. New code should use NanoMemControlService.
NanoMemAdminService = NanoMemControlService
