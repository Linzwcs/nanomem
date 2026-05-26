from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from nanomem.service.control.service import (
    BackupResult,
    ExportResult,
    IntegrityCheckResult,
    NanoMemControlService,
    OperationLogRetentionApplyResult,
    OperationLogRetentionPolicy,
    OperationLogRetentionPreview,
    ReindexResult,
    RetentionApplyResult,
    RetentionPolicy,
    RetentionPreview,
    SchemaStatus,
)
from nanomem.core.config import MaintenanceConfig, RetentionConfig
from nanomem.core.errors import ConfigError


@dataclass(frozen=True)
class MaintenancePlan:
    schema_status: SchemaStatus
    integrity_check: IntegrityCheckResult | None = None
    retention_preview: RetentionPreview | None = None
    operation_log_retention_preview: OperationLogRetentionPreview | None = None
    planned_actions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MaintenanceRunResult:
    plan: MaintenancePlan
    backup: BackupResult | None = None
    export: ExportResult | None = None
    retention: RetentionApplyResult | None = None
    operation_log_retention: OperationLogRetentionApplyResult | None = None
    reindex: ReindexResult | None = None
    integrity_after: IntegrityCheckResult | None = None
    warnings: tuple[str, ...] = ()


class NanoMemMaintenanceService:
    def __init__(
        self,
        *,
        control: NanoMemControlService,
        config: MaintenanceConfig,
    ) -> None:
        self.control = control
        self.config = config

    def plan(self) -> MaintenancePlan:
        schema_status = self.control.schema_status()
        integrity = (
            self.control.integrity_check()
            if self.config.integrity_check
            else None
        )
        retention_policy = _retention_policy(self.config.retention)
        log_policy = _log_retention_policy(self.config.operation_log_retention)
        retention_preview = (
            self.control.retention_preview(retention_policy)
            if retention_policy is not None
            else None
        )
        log_preview = (
            self.control.operation_log_retention_preview(log_policy)
            if log_policy is not None
            else None
        )
        return MaintenancePlan(
            schema_status=schema_status,
            integrity_check=integrity,
            retention_preview=retention_preview,
            operation_log_retention_preview=log_preview,
            planned_actions=_planned_actions(
                self.config,
                retention_preview=retention_preview,
                log_preview=log_preview,
            ),
            warnings=_warnings(
                self.config,
                schema_status=schema_status,
                integrity=integrity,
            ),
        )

    def run(self) -> MaintenanceRunResult:
        plan = self.plan()
        backup = None
        export = None
        retention = None
        log_retention = None
        reindex = None

        if self.config.backup.enabled:
            if not self.config.backup.path:
                raise ConfigError("maintenance.backup.path is required")
            backup = self.control.backup(
                self.config.backup.path,
                overwrite=self.config.backup.overwrite,
            )

        if self.config.export.enabled:
            if not self.config.export.path:
                raise ConfigError("maintenance.export.path is required")
            export = self.control.export_json(
                self.config.export.path,
                include_operation_logs=(
                    self.config.export.include_operation_logs
                ),
                overwrite=self.config.export.overwrite,
            )

        retention_policy = _retention_policy(self.config.retention)
        if retention_policy is not None:
            retention = self.control.retention_apply(retention_policy)

        log_policy = _log_retention_policy(self.config.operation_log_retention)
        if log_policy is not None:
            log_retention = self.control.operation_log_retention_apply(log_policy)

        if retention is None and "reindex" in plan.planned_actions:
            reindex = self.control.reindex()

        integrity_after = (
            self.control.integrity_check()
            if self.config.integrity_check
            else None
        )
        return MaintenanceRunResult(
            plan=plan,
            backup=backup,
            export=export,
            retention=retention,
            operation_log_retention=log_retention,
            reindex=reindex,
            integrity_after=integrity_after,
            warnings=plan.warnings,
        )


def _planned_actions(
    config: MaintenanceConfig,
    *,
    retention_preview: RetentionPreview | None,
    log_preview: OperationLogRetentionPreview | None,
) -> tuple[str, ...]:
    actions: list[str] = []
    if config.integrity_check:
        actions.append("integrity_check")
    if config.backup.enabled:
        actions.append("backup")
    if config.export.enabled:
        actions.append("export")
    if retention_preview is not None:
        actions.append("unit_retention")
        if retention_preview.matched_unit_count > 0:
            actions.append("reindex")
    if log_preview is not None:
        actions.append("operation_log_retention")
    return tuple(actions)


def _warnings(
    config: MaintenanceConfig,
    *,
    schema_status: SchemaStatus,
    integrity: IntegrityCheckResult | None,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if schema_status.needs_migration:
        warnings.append("schema_migration_pending")
    if integrity is not None and not integrity.ok:
        warnings.append("integrity_check_failed")
    if config.backup.enabled and not config.backup.path:
        warnings.append("backup_enabled_without_path")
    if config.export.enabled and not config.export.path:
        warnings.append("export_enabled_without_path")
    if config.retention.enabled and _retention_cutoff(config.retention) is None:
        warnings.append("retention_enabled_without_cutoff")
    if (
        config.operation_log_retention.enabled
        and _retention_cutoff(config.operation_log_retention) is None
    ):
        warnings.append("operation_log_retention_enabled_without_cutoff")
    return tuple(warnings)


def _retention_policy(config: RetentionConfig) -> RetentionPolicy | None:
    cutoff = _retention_cutoff(config)
    if not config.enabled or cutoff is None:
        return None
    return RetentionPolicy(before=cutoff)


def _log_retention_policy(
    config: RetentionConfig,
) -> OperationLogRetentionPolicy | None:
    cutoff = _retention_cutoff(config)
    if not config.enabled or cutoff is None:
        return None
    return OperationLogRetentionPolicy(before=cutoff)


def _retention_cutoff(config: RetentionConfig) -> str | None:
    if config.before:
        return config.before
    if config.max_age_days is None:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.max_age_days)
    return cutoff.date().isoformat()
