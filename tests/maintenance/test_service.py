from __future__ import annotations

from nanomem.core.config import (
    BackupConfig,
    ExportConfig,
    MaintenanceConfig,
    RetentionConfig,
)
from nanomem.ops.control.service import NanoMemControlService
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.ops.maintenance.service import NanoMemMaintenanceService
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore


def _make_maintenance(tmp_path, config: MaintenanceConfig) -> NanoMemMaintenanceService:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    control = NanoMemControlService(store=store, index=DenseMemoryUnitIndex())
    return NanoMemMaintenanceService(control=control, config=config)


def test_plan_with_minimal_config_is_clean(tmp_path) -> None:
    config = MaintenanceConfig(
        integrity_check=False,
        backup=BackupConfig(enabled=False),
        export=ExportConfig(enabled=False),
        retention=RetentionConfig(enabled=False),
        operation_log_retention=RetentionConfig(enabled=False),
    )
    service = _make_maintenance(tmp_path, config)

    plan = service.plan()

    assert plan.warnings == ()
    assert plan.integrity_check is None
    assert plan.retention_preview is None


def test_plan_includes_integrity_when_enabled(tmp_path) -> None:
    config = MaintenanceConfig(
        integrity_check=True,
        backup=BackupConfig(enabled=False),
        export=ExportConfig(enabled=False),
        retention=RetentionConfig(enabled=False),
        operation_log_retention=RetentionConfig(enabled=False),
    )
    service = _make_maintenance(tmp_path, config)

    plan = service.plan()

    assert plan.integrity_check is not None
    assert plan.integrity_check.ok is True
    assert "integrity_check" in plan.planned_actions


def test_run_with_no_actions_returns_clean_result(tmp_path) -> None:
    config = MaintenanceConfig(
        integrity_check=False,
        backup=BackupConfig(enabled=False),
        export=ExportConfig(enabled=False),
        retention=RetentionConfig(enabled=False),
        operation_log_retention=RetentionConfig(enabled=False),
    )
    service = _make_maintenance(tmp_path, config)

    result = service.run()

    assert result.backup is None
    assert result.export is None
    assert result.retention is None
    assert result.operation_log_retention is None


def test_run_executes_backup_when_configured(tmp_path) -> None:
    backup_path = tmp_path / "backup.db"
    config = MaintenanceConfig(
        integrity_check=False,
        backup=BackupConfig(enabled=True, path=str(backup_path), overwrite=False),
        export=ExportConfig(enabled=False),
        retention=RetentionConfig(enabled=False),
        operation_log_retention=RetentionConfig(enabled=False),
    )
    service = _make_maintenance(tmp_path, config)

    result = service.run()

    assert result.backup is not None
    assert backup_path.exists()
