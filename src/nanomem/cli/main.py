from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from typing import TextIO

from nanomem.control import (
    NanoMemControlService,
    OperationLogRetentionPolicy,
    RetentionPolicy,
)
from nanomem.config import NanoMemConfig, load_config
from nanomem.contracts import MemoryScope, MemoryUnit, TimeRange
from nanomem.factory import index_from_config
from nanomem.maintenance import NanoMemMaintenanceService
from nanomem.store.sqlite import SQLiteMemoryUnitStore
from nanomem.tui.dashboard import (
    build_dashboard,
    render_dashboard,
    run_dashboard_watch,
)


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    output = stdout or sys.stdout
    parser = _parser()
    args = parser.parse_args(argv)
    config = load_config(args.config) if getattr(args, "config", None) else None
    store = _store_from_args(args, config)
    try:
        control = NanoMemControlService(
            store=store,
            index=index_from_config(config) if config is not None else None,
        )
        if args.command == "stats":
            return _stats(control, json_output=args.json, stdout=output)
        if args.command == "list":
            return _list(control, args=args, stdout=output)
        if args.command == "logs":
            return _logs(control, args=args, stdout=output)
        if args.command == "migrations":
            return _migrations(control, json_output=args.json, stdout=output)
        if args.command == "integrity-check":
            return _integrity_check(control, json_output=args.json, stdout=output)
        if args.command == "backup":
            return _backup(control, args=args, stdout=output)
        if args.command == "export":
            return _export(control, args=args, stdout=output)
        if args.command == "maintenance-plan":
            return _maintenance_plan(
                _maintenance_service(control, config),
                json_output=args.json,
                stdout=output,
            )
        if args.command == "maintenance-run":
            return _maintenance_run(
                _maintenance_service(control, config),
                args=args,
                stdout=output,
            )
        if args.command == "reindex":
            return _reindex(control, json_output=args.json, stdout=output)
        if args.command == "retention-preview":
            return _retention_preview(control, args=args, stdout=output)
        if args.command == "retention-apply":
            return _retention_apply(control, args=args, stdout=output)
        if args.command == "log-retention-preview":
            return _log_retention_preview(control, args=args, stdout=output)
        if args.command == "log-retention-apply":
            return _log_retention_apply(control, args=args, stdout=output)
        if args.command == "dashboard":
            return _dashboard(control, args=args, stdout=output)
    finally:
        store.close()
    parser.error(f"unknown command: {args.command}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nanomem")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats = subparsers.add_parser("stats", help="Show NanoMem database stats.")
    _add_db_or_config_args(stats)
    stats.add_argument("--json", action="store_true", help="Emit JSON.")

    list_cmd = subparsers.add_parser("list", help="List units.")
    _add_db_or_config_args(list_cmd)
    list_cmd.add_argument("--tenant-id")
    list_cmd.add_argument("--user-id")
    list_cmd.add_argument("--agent-id")
    list_cmd.add_argument("--project-id")
    list_cmd.add_argument("--session-id")
    list_cmd.add_argument("--from", dest="start")
    list_cmd.add_argument("--to", dest="end")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.add_argument("--json", action="store_true", help="Emit JSON.")

    logs = subparsers.add_parser("logs", help="List capture/read operation logs.")
    _add_db_or_config_args(logs)
    logs.add_argument("--tenant-id")
    logs.add_argument("--user-id")
    logs.add_argument("--agent-id")
    logs.add_argument("--project-id")
    logs.add_argument("--session-id")
    logs.add_argument("--type", dest="operation_type", choices=("capture", "read"))
    logs.add_argument("--limit", type=int, default=20)
    logs.add_argument("--json", action="store_true", help="Emit JSON.")

    migrations = subparsers.add_parser(
        "migrations",
        help="Show schema migration status.",
    )
    _add_db_or_config_args(migrations)
    migrations.add_argument("--json", action="store_true", help="Emit JSON.")

    integrity = subparsers.add_parser(
        "integrity-check",
        help="Run SQLite PRAGMA integrity_check.",
    )
    _add_db_or_config_args(integrity)
    integrity.add_argument("--json", action="store_true", help="Emit JSON.")

    backup = subparsers.add_parser(
        "backup",
        help="Create a physical SQLite backup.",
    )
    _add_db_or_config_args(backup)
    backup.add_argument("--output", required=True, help="Backup database path.")
    backup.add_argument("--overwrite", action="store_true")
    backup.add_argument("--json", action="store_true", help="Emit JSON.")

    export = subparsers.add_parser(
        "export",
        help="Export units and optional operation logs as JSON.",
    )
    _add_db_or_config_args(export)
    export.add_argument("--output", required=True, help="Export JSON path.")
    export.add_argument("--no-logs", action="store_true")
    export.add_argument("--overwrite", action="store_true")
    export.add_argument("--json", action="store_true", help="Emit JSON.")

    maintenance_plan = subparsers.add_parser(
        "maintenance-plan",
        help="Preview configured maintenance actions.",
    )
    maintenance_plan.add_argument(
        "--config",
        required=True,
        help="NanoMem config YAML/JSON path.",
    )
    maintenance_plan.add_argument("--json", action="store_true", help="Emit JSON.")

    maintenance_run = subparsers.add_parser(
        "maintenance-run",
        help="Run configured maintenance actions.",
    )
    maintenance_run.add_argument(
        "--config",
        required=True,
        help="NanoMem config YAML/JSON path.",
    )
    maintenance_run.add_argument(
        "--yes",
        action="store_true",
        help="Confirm configured maintenance actions.",
    )
    maintenance_run.add_argument("--json", action="store_true", help="Emit JSON.")

    reindex = subparsers.add_parser("reindex", help="Rebuild the active index.")
    _add_db_or_config_args(reindex)
    reindex.add_argument("--json", action="store_true", help="Emit JSON.")

    retention_preview = subparsers.add_parser(
        "retention-preview",
        help="Preview units that would be removed by retention.",
    )
    _add_retention_args(retention_preview)

    retention_apply = subparsers.add_parser(
        "retention-apply",
        help="Apply retention deletion to units older than --before.",
    )
    _add_retention_args(retention_apply)
    retention_apply.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion.",
    )

    log_retention_preview = subparsers.add_parser(
        "log-retention-preview",
        help="Preview operation logs that would be removed by retention.",
    )
    _add_log_retention_args(log_retention_preview)

    log_retention_apply = subparsers.add_parser(
        "log-retention-apply",
        help="Apply retention deletion to operation logs older than --before.",
    )
    _add_log_retention_args(log_retention_apply)
    log_retention_apply.add_argument(
        "--yes",
        action="store_true",
        help="Confirm deletion.",
    )

    dashboard = subparsers.add_parser(
        "dashboard",
        help="Render a read-only NanoMem terminal dashboard.",
    )
    _add_db_or_config_args(dashboard)
    dashboard.add_argument("--limit", type=int, default=10)
    dashboard.add_argument(
        "--watch",
        action="store_true",
        help="Refresh the dashboard until interrupted.",
    )
    dashboard.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Watch refresh interval in seconds.",
    )
    dashboard.add_argument(
        "--iterations",
        type=int,
        help="Maximum watch refresh count. Useful for scripts and tests.",
    )
    dashboard.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear the terminal between watch refreshes.",
    )
    dashboard.add_argument(
        "--retention-before",
        help="Include a retention preview for units older than this value.",
    )
    return parser


def _stats(
    control: NanoMemControlService,
    *,
    json_output: bool,
    stdout: TextIO,
) -> int:
    stats = control.stats()
    payload = asdict(stats)
    if json_output:
        _write_json(payload, stdout)
        return 0
    stdout.write("NanoMem database\n")
    stdout.write(f"  store: {stats.store}\n")
    stdout.write(f"  path: {stats.path}\n")
    stdout.write(f"  schema_version: {stats.schema_version}\n")
    stdout.write(f"  latest_schema_version: {stats.latest_schema_version}\n")
    stdout.write(
        f"  applied_schema_migrations: "
        f"{stats.applied_schema_migration_count}\n"
    )
    stdout.write(
        f"  pending_schema_migrations: "
        f"{stats.pending_schema_migration_count}\n"
    )
    stdout.write(f"  file_size_bytes: {stats.file_size_bytes}\n")
    stdout.write(f"  units: {stats.unit_count}\n")
    stdout.write(f"  owners: {stats.owner_count}\n")
    stdout.write(f"  namespaces: {stats.namespace_count}\n")
    stdout.write(f"  dialogues: {stats.dialogue_count}\n")
    stdout.write(f"  operation_logs: {stats.operation_log_count}\n")
    stdout.write(f"  latest_operation_at: {stats.latest_operation_at}\n")
    stdout.write(f"  oldest_timestamp: {stats.oldest_timestamp}\n")
    stdout.write(f"  newest_timestamp: {stats.newest_timestamp}\n")
    stdout.write(f"  index_backend: {stats.index_backend}\n")
    stdout.write(f"  index_document_count: {stats.index_document_count}\n")
    return 0


def _migrations(
    control: NanoMemControlService,
    *,
    json_output: bool,
    stdout: TextIO,
) -> int:
    status = control.schema_status()
    payload = asdict(status)
    if json_output:
        _write_json(payload, stdout)
        return 0
    stdout.write("Schema migrations\n")
    stdout.write(f"  schema_version: {status.schema_version}\n")
    stdout.write(f"  latest_schema_version: {status.latest_schema_version}\n")
    stdout.write(f"  needs_migration: {status.needs_migration}\n")
    stdout.write("  applied:\n")
    if status.applied:
        for item in status.applied:
            stdout.write(
                f"    {item.version}: {item.name} "
                f"at {item.applied_at}\n"
            )
    else:
        stdout.write("    none\n")
    stdout.write("  pending:\n")
    if status.pending:
        for item in status.pending:
            stdout.write(f"    {item.version}: {item.name}\n")
    else:
        stdout.write("    none\n")
    return 0


def _integrity_check(
    control: NanoMemControlService,
    *,
    json_output: bool,
    stdout: TextIO,
) -> int:
    result = control.integrity_check()
    payload = asdict(result)
    if json_output:
        _write_json(payload, stdout)
        return 0 if result.ok else 1
    stdout.write("SQLite integrity_check\n")
    stdout.write(f"  ok: {result.ok}\n")
    for message in result.messages:
        stdout.write(f"  message: {message}\n")
    return 0 if result.ok else 1


def _backup(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    try:
        result = control.backup(args.output, overwrite=args.overwrite)
    except FileExistsError as exc:
        stdout.write(f"{exc}\n")
        return 2
    payload = asdict(result)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write(
        f"Backup written to {result.path} "
        f"({result.file_size_bytes} bytes).\n"
    )
    return 0


def _export(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    try:
        result = control.export_json(
            args.output,
            include_operation_logs=not args.no_logs,
            overwrite=args.overwrite,
        )
    except FileExistsError as exc:
        stdout.write(f"{exc}\n")
        return 2
    payload = asdict(result)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write(
        f"Export written to {result.path}: {result.unit_count} units, "
        f"{result.operation_log_count} operation logs.\n"
    )
    return 0


def _maintenance_plan(
    service: NanoMemMaintenanceService,
    *,
    json_output: bool,
    stdout: TextIO,
) -> int:
    plan = service.plan()
    payload = asdict(plan)
    if json_output:
        _write_json(payload, stdout)
        return 0
    stdout.write("Maintenance plan\n")
    stdout.write(f"  schema_version: {plan.schema_status.schema_version}\n")
    stdout.write(
        f"  latest_schema_version: "
        f"{plan.schema_status.latest_schema_version}\n"
    )
    stdout.write(f"  needs_migration: {plan.schema_status.needs_migration}\n")
    if plan.integrity_check is not None:
        stdout.write(f"  integrity_ok: {plan.integrity_check.ok}\n")
    if plan.retention_preview is not None:
        stdout.write(
            f"  retention_matched_units: "
            f"{plan.retention_preview.matched_unit_count}\n"
        )
    if plan.operation_log_retention_preview is not None:
        stdout.write(
            f"  log_retention_matched_logs: "
            f"{plan.operation_log_retention_preview.matched_log_count}\n"
        )
    stdout.write(f"  planned_actions: {_csv(plan.planned_actions)}\n")
    stdout.write(f"  warnings: {_csv(plan.warnings)}\n")
    return 0


def _maintenance_run(
    service: NanoMemMaintenanceService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    if not args.yes:
        stdout.write("Refusing to run maintenance without --yes.\n")
        return 2
    try:
        result = service.run()
    except FileExistsError as exc:
        stdout.write(f"{exc}\n")
        return 2
    payload = asdict(result)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write("Maintenance run completed\n")
    stdout.write(f"  actions: {_csv(result.plan.planned_actions)}\n")
    if result.backup is not None:
        stdout.write(f"  backup: {result.backup.path}\n")
    if result.export is not None:
        stdout.write(f"  export: {result.export.path}\n")
    if result.retention is not None:
        stdout.write(
            f"  deleted_units: {result.retention.deleted_unit_count}\n"
        )
    if result.operation_log_retention is not None:
        stdout.write(
            f"  deleted_operation_logs: "
            f"{result.operation_log_retention.deleted_log_count}\n"
        )
    if result.integrity_after is not None:
        stdout.write(f"  integrity_ok: {result.integrity_after.ok}\n")
    stdout.write(f"  warnings: {_csv(result.warnings)}\n")
    return 0


def _list(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    scope = _scope_from_args(args)
    units = control.list_units(
        scope=scope,
        time_range=TimeRange(start=args.start, end=args.end),
        limit=args.limit,
    )
    if args.json:
        _write_json([_unit_payload(item) for item in units], stdout)
        return 0
    for unit in units:
        refs = ",".join(ref.dialogue_id for ref in unit.dialogue_refs) or "none"
        timestamp = unit.timestamp or unit.available_at
        stdout.write(
            f"{timestamp}\t{unit.scope.owner_id}\t{unit.scope.namespace}\t"
            f"{unit.unit_id}\t{refs}\t{unit.text}\n"
        )
    return 0


def _logs(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    logs = control.list_operation_logs(
        scope=_scope_from_args(args),
        operation_type=args.operation_type,
        limit=args.limit,
    )
    if args.json:
        _write_json([asdict(item) for item in logs], stdout)
        return 0
    for item in logs:
        summary = item.summary
        owner_id = item.scope.owner_id if item.scope else ""
        stdout.write(
            f"{item.created_at}\t{item.operation_type}\t{item.status}\t"
            f"{owner_id}\t"
        )
        if item.operation_type == "read":
            stdout.write(
                f"query={summary.get('query', '')}\t"
                f"returned_units={summary.get('returned_unit_count', '')}\n"
            )
        else:
            stdout.write(
                f"events={summary.get('event_count', '')}\t"
                f"units={summary.get('unit_count', '')}\n"
            )
    return 0


def _reindex(
    control: NanoMemControlService,
    *,
    json_output: bool,
    stdout: TextIO,
) -> int:
    result = control.reindex()
    payload = asdict(result)
    if json_output:
        _write_json(payload, stdout)
        return 0
    stdout.write(
        f"Indexed {result.indexed_unit_count} units "
        f"into {result.index_backend}.\n"
    )
    return 0


def _retention_preview(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    policy = _retention_policy_from_args(args)
    preview = control.retention_preview(policy)
    payload = asdict(preview)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write("Retention preview\n")
    stdout.write(f"  before: {policy.before}\n")
    stdout.write(f"  matched_units: {preview.matched_unit_count}\n")
    stdout.write(f"  oldest_timestamp: {preview.oldest_timestamp}\n")
    stdout.write(f"  newest_timestamp: {preview.newest_timestamp}\n")
    for unit in preview.sample_units:
        timestamp = unit.timestamp or unit.available_at
        stdout.write(
            f"  sample: {timestamp} {unit.unit_id} "
            f"{unit.text}\n"
        )
    return 0


def _retention_apply(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    if not args.yes:
        stdout.write("Refusing to apply retention without --yes.\n")
        return 2
    policy = _retention_policy_from_args(args)
    result = control.retention_apply(policy)
    payload = asdict(result)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write(
        f"Deleted {result.deleted_unit_count} units before "
        f"{policy.before}; reindexed {result.reindex.indexed_unit_count} "
        f"remaining units.\n"
    )
    return 0


def _log_retention_preview(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    policy = _log_retention_policy_from_args(args)
    preview = control.operation_log_retention_preview(policy)
    payload = asdict(preview)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write("Operation log retention preview\n")
    stdout.write(f"  before: {policy.before}\n")
    stdout.write(f"  operation_type: {policy.operation_type}\n")
    stdout.write(f"  matched_logs: {preview.matched_log_count}\n")
    stdout.write(f"  oldest_created_at: {preview.oldest_created_at}\n")
    stdout.write(f"  newest_created_at: {preview.newest_created_at}\n")
    for log in preview.sample_logs:
        owner_id = log.scope.owner_id if log.scope else ""
        stdout.write(
            f"  sample: {log.created_at} {log.operation_type} "
            f"{log.status} {owner_id}\n"
        )
    return 0


def _log_retention_apply(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    if not args.yes:
        stdout.write("Refusing to apply operation log retention without --yes.\n")
        return 2
    policy = _log_retention_policy_from_args(args)
    result = control.operation_log_retention_apply(policy)
    payload = asdict(result)
    if args.json:
        _write_json(payload, stdout)
        return 0
    stdout.write(
        f"Deleted {result.deleted_log_count} operation logs before "
        f"{policy.before}.\n"
    )
    return 0


def _dashboard(
    control: NanoMemControlService,
    *,
    args: argparse.Namespace,
    stdout: TextIO,
) -> int:
    if args.watch:
        run_dashboard_watch(
            control,
            stdout=stdout,
            limit=args.limit,
            retention_before=args.retention_before,
            interval_seconds=args.interval,
            iterations=args.iterations,
            clear_screen=not args.no_clear,
        )
        return 0
    snapshot = build_dashboard(
        control,
        limit=args.limit,
        retention_before=args.retention_before,
    )
    stdout.write(render_dashboard(snapshot))
    return 0


def _add_retention_args(parser: argparse.ArgumentParser) -> None:
    _add_db_or_config_args(parser)
    parser.add_argument(
        "--before",
        required=True,
        help="Delete units older than this timestamp/date.",
    )
    parser.add_argument("--tenant-id")
    parser.add_argument("--user-id")
    parser.add_argument("--agent-id")
    parser.add_argument("--project-id")
    parser.add_argument("--session-id")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")


def _add_log_retention_args(parser: argparse.ArgumentParser) -> None:
    _add_db_or_config_args(parser)
    parser.add_argument(
        "--before",
        required=True,
        help="Delete operation logs older than this timestamp/date.",
    )
    parser.add_argument("--tenant-id")
    parser.add_argument("--user-id")
    parser.add_argument("--agent-id")
    parser.add_argument("--project-id")
    parser.add_argument("--session-id")
    parser.add_argument("--type", dest="operation_type", choices=("capture", "read"))
    parser.add_argument("--json", action="store_true", help="Emit JSON.")


def _retention_policy_from_args(args: argparse.Namespace) -> RetentionPolicy:
    return RetentionPolicy(
        before=args.before,
        scope=_scope_from_args(args),
    )


def _log_retention_policy_from_args(
    args: argparse.Namespace,
) -> OperationLogRetentionPolicy:
    return OperationLogRetentionPolicy(
        before=args.before,
        scope=_scope_from_args(args),
        operation_type=args.operation_type,
    )


def _add_db_or_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", help="SQLite database path.")
    parser.add_argument("--config", help="NanoMem config YAML/JSON path.")


def _store_from_args(
    args: argparse.Namespace,
    config: NanoMemConfig | None,
) -> SQLiteMemoryUnitStore:
    if config is not None:
        if config.store.backend != "sqlite":
            raise SystemExit(f"Unsupported store backend: {config.store.backend}")
        return SQLiteMemoryUnitStore(config.store.path)
    if not getattr(args, "db", None):
        raise SystemExit("--db or --config is required")
    return SQLiteMemoryUnitStore(args.db)


def _maintenance_service(
    control: NanoMemControlService,
    config: NanoMemConfig | None,
) -> NanoMemMaintenanceService:
    if config is None:
        raise SystemExit("--config is required")
    return NanoMemMaintenanceService(
        control=control,
        config=config.maintenance,
    )


def _scope_from_args(args: argparse.Namespace) -> MemoryScope | None:
    if not any(
        (
            args.user_id,
        )
    ):
        return None
    if not args.user_id:
        raise SystemExit("--user-id is required when scope filters are provided")
    return MemoryScope(
        owner_id=args.user_id,
        namespace=None,
    )


def _unit_payload(unit: MemoryUnit) -> dict[str, object]:
    return asdict(unit)


def _write_json(payload: object, stdout: TextIO) -> None:
    stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    stdout.write("\n")


def _csv(items: tuple[str, ...]) -> str:
    if not items:
        return "none"
    return ", ".join(items)
