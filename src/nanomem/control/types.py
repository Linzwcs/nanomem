"""Result and policy dataclasses for the control plane.

These are the stable public types that the manager UI, CLI, and the
narrow :class:`~nanomem.service.facade.ControlFacade` build on.
:class:`NanoMemControlService` lives in :mod:`nanomem.control.service`
and consumes these types.

All dataclasses are frozen — treat them as immutable values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nanomem.core.contracts import (
    MemoryScope,
    MemoryUnit,
    OperationLogEntry,
    ReindexResult,
)


@dataclass(frozen=True)
class DatabaseStats:
    store: str
    path: str
    file_size_bytes: int | None
    schema_version: int
    latest_schema_version: int
    unit_count: int
    active_unit_count: int
    owner_count: int
    namespace_count: int
    session_count: int
    dialogue_count: int
    dialogue_window_count: int
    open_dialogue_window_count: int
    operation_log_count: int
    applied_schema_migration_count: int = 0
    pending_schema_migration_count: int = 0
    latest_operation_at: str | None = None
    oldest_timestamp: str | None = None
    newest_timestamp: str | None = None
    top_owners: tuple[dict[str, Any], ...] = ()
    index_backend: str | None = None
    index_document_count: int | None = None
    index_health: str = "unknown"
    index_unit_delta: int | None = None
    last_reindex_at: str | None = None
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


__all__ = [
    "BackupResult",
    "DatabaseStats",
    "ExportResult",
    "IntegrityCheckResult",
    "OperationLogRetentionApplyResult",
    "OperationLogRetentionPolicy",
    "OperationLogRetentionPreview",
    "PendingSchemaMigration",
    "RetentionApplyResult",
    "RetentionPolicy",
    "RetentionPreview",
    "SchemaMigrationRecord",
    "SchemaStatus",
]
