"""Control-plane services for operators, CLI, and the manager UI.

Public surface is split between:

- :mod:`nanomem.control.types` — frozen result and policy dataclasses
- :mod:`nanomem.control.service` — :class:`NanoMemControlService` itself

Both are re-exported here so existing
``from nanomem.control import X`` import sites continue to work.
"""

from __future__ import annotations

from nanomem.contracts import OperationLogEntry, ReindexResult
from nanomem.control.service import (
    NanoMemAdminService,
    NanoMemControlService,
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

__all__ = [
    "BackupResult",
    "DatabaseStats",
    "ExportResult",
    "IntegrityCheckResult",
    "NanoMemAdminService",
    "NanoMemControlService",
    "OperationLogEntry",
    "OperationLogRetentionApplyResult",
    "OperationLogRetentionPolicy",
    "OperationLogRetentionPreview",
    "PendingSchemaMigration",
    "ReindexResult",
    "RetentionApplyResult",
    "RetentionPolicy",
    "RetentionPreview",
    "SchemaMigrationRecord",
    "SchemaStatus",
]
