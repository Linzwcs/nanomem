"""Terminal UI for the nanomem control plane.

Status: experimental. The dashboard is wired into the CLI via
``nanomem dashboard`` and is intended for **operators** inspecting
local state, not for agent-facing tools. Public API may shift.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TextIO

from nanomem.service.control import (
    DatabaseStats,
    NanoMemControlService,
    RetentionPolicy,
    RetentionPreview,
)
from nanomem.core.contracts import MemoryUnit, OperationLogEntry
from nanomem.core.time import now_utc_iso


@dataclass(frozen=True)
class MonitorHealth:
    status: str
    index_lag: int | None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class DashboardSnapshot:
    generated_at: str
    stats: DatabaseStats
    health: MonitorHealth
    recent_units: tuple[MemoryUnit, ...]
    recent_logs: tuple[OperationLogEntry, ...]
    retention_preview: RetentionPreview | None = None


def build_dashboard(
    control: NanoMemControlService,
    *,
    limit: int = 10,
    retention_before: str | None = None,
) -> DashboardSnapshot:
    retention = None
    if retention_before:
        retention = control.retention_preview(
            RetentionPolicy(before=retention_before),
            sample_limit=min(limit, 10),
        )
    stats = control.stats()
    return DashboardSnapshot(
        generated_at=now_utc_iso(),
        stats=stats,
        health=_health_from_stats(stats),
        recent_units=control.list_units(limit=limit),
        recent_logs=control.list_operation_logs(limit=limit),
        retention_preview=retention,
    )


def render_dashboard(snapshot: DashboardSnapshot) -> str:
    lines: list[str] = [
        "NanoMem Dashboard",
        f"generated_at: {snapshot.generated_at}",
        "",
        "Monitor",
        f"  status: {snapshot.health.status}",
        f"  index_lag: {_value(snapshot.health.index_lag)}",
        f"  issues: {_issues(snapshot.health.issues)}",
        "",
        "Overview",
        f"  store: {snapshot.stats.store}",
        f"  path: {snapshot.stats.path}",
        f"  schema_version: {snapshot.stats.schema_version}",
        f"  latest_schema_version: {snapshot.stats.latest_schema_version}",
        (
            "  schema_migrations: "
            f"applied={snapshot.stats.applied_schema_migration_count}, "
            f"pending={snapshot.stats.pending_schema_migration_count}"
        ),
        f"  file_size_bytes: {_value(snapshot.stats.file_size_bytes)}",
        f"  units: {snapshot.stats.unit_count}",
        f"  owners: {snapshot.stats.owner_count}",
        f"  namespaces: {snapshot.stats.namespace_count}",
        f"  dialogues: {snapshot.stats.dialogue_count}",
        f"  operation_logs: {snapshot.stats.operation_log_count}",
        f"  latest_operation_at: {_value(snapshot.stats.latest_operation_at)}",
        f"  oldest_timestamp: {_value(snapshot.stats.oldest_timestamp)}",
        f"  newest_timestamp: {_value(snapshot.stats.newest_timestamp)}",
        "",
        "Index",
        f"  backend: {_value(snapshot.stats.index_backend)}",
        f"  documents: {_value(snapshot.stats.index_document_count)}",
    ]
    lines.extend(_index_metadata_lines(snapshot.stats.metadata.get("index")))
    lines.extend(["", "Top Owners"])
    if snapshot.stats.top_owners:
        for row in snapshot.stats.top_owners:
            owner_id = _value(row.get("owner_id"))
            namespace = _value(row.get("namespace"))
            count = _value(row.get("unit_count"))
            lines.append(f"  {owner_id}/{namespace}: {count}")
    else:
        lines.append("  none")

    lines.extend(["", "Recent Operation Logs"])
    if snapshot.recent_logs:
        for log in snapshot.recent_logs:
            lines.extend(_operation_log_lines(log))
    else:
        lines.append("  none")

    lines.extend(["", "Recent Memory Units"])
    if snapshot.recent_units:
        for unit in snapshot.recent_units:
            lines.append(_unit_line(unit))
    else:
        lines.append("  none")

    if snapshot.retention_preview is not None:
        preview = snapshot.retention_preview
        lines.extend([
            "",
            "Retention Preview",
            f"  before: {preview.policy.before}",
            f"  matched_units: {preview.matched_unit_count}",
            f"  oldest_timestamp: {_value(preview.oldest_timestamp)}",
            f"  newest_timestamp: {_value(preview.newest_timestamp)}",
        ])
        if preview.sample_units:
            lines.append("  samples:")
            for unit in preview.sample_units:
                lines.append(_unit_line(unit, indent="    "))
        else:
            lines.append("  samples: none")

    return "\n".join(lines) + "\n"


def run_dashboard_watch(
    control: NanoMemControlService,
    *,
    stdout: TextIO,
    limit: int = 10,
    retention_before: str | None = None,
    interval_seconds: float = 2.0,
    iterations: int | None = None,
    clear_screen: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    count = 0
    while iterations is None or count < iterations:
        snapshot = build_dashboard(
            control,
            limit=limit,
            retention_before=retention_before,
        )
        if clear_screen:
            stdout.write("\033[2J\033[H")
        stdout.write(render_dashboard(snapshot))
        stdout.flush()
        count += 1
        if iterations is not None and count >= iterations:
            break
        sleep(interval_seconds)


def _unit_line(
    unit: MemoryUnit,
    *,
    indent: str = "  ",
) -> str:
    timestamp = unit.timestamp or unit.available_at
    refs = ",".join(ref.dialogue_id for ref in unit.dialogue_refs) or "none"
    return (
        f"{indent}{timestamp} | {unit.scope.owner_id}/{unit.scope.namespace} | "
        f"{refs} | {unit.text}"
    )


def _operation_log_lines(log: OperationLogEntry) -> list[str]:
    summary = log.summary
    lines = [
        (
            f"  {log.created_at} | {log.operation_type} | {log.status} | "
            f"{log.scope.owner_id if log.scope else ''}"
        )
    ]
    if log.operation_type == "read":
        query = _value(summary.get("query"))
        returned = _value(summary.get("returned_unit_count"))
        context_tokens = _value(summary.get("context_tokens"))
        lines.append(
            f"    query: {_truncate(query, 96)}"
        )
        lines.append(
            f"    returned_units: {returned} | context_tokens: {context_tokens}"
        )
        response_text = str(log.payload.get("response_text") or "")
        if response_text:
            lines.append(f"    response: {_truncate(response_text, 140)}")
        ranked_units = log.payload.get("ranked_units")
        if isinstance(ranked_units, list) and ranked_units:
            top = ranked_units[0]
            if isinstance(top, dict):
                lines.append(
                    "    top_unit: "
                    f"{_value(top.get('unit_id'))} "
                    f"score={_value(top.get('score'))} "
                    f"text={_truncate(_value(top.get('text')), 100)}"
                )
    elif log.operation_type == "capture":
        lines.append(
            "    events: "
            f"{_value(summary.get('event_count'))} | accepted: "
            f"{_value(summary.get('accepted_event_count'))} | units: "
            f"{_value(summary.get('unit_count'))} | skipped: "
            f"{_value(summary.get('skipped_count'))}"
        )
        units = log.payload.get("units")
        if isinstance(units, list) and units:
            first = units[0]
            if isinstance(first, dict):
                lines.append(
                    "    first_unit: "
                    f"{_value(first.get('unit_id'))} "
                    f"text={_truncate(_value(first.get('text')), 100)}"
                )
    else:
        lines.append(f"    summary: {_truncate(str(summary), 140)}")
    return lines


def _index_metadata_lines(metadata: object) -> list[str]:
    if not isinstance(metadata, dict):
        return []
    lines: list[str] = []
    backend = metadata.get("backend")
    if backend is not None:
        lines.append(f"  backend: {_value(backend)}")
    embedding_model = metadata.get("embedding_model")
    if embedding_model is not None:
        lines.append(f"  embedding_model: {_value(embedding_model)}")
    stats = metadata.get("stats")
    if isinstance(stats, dict):
        for key in (
            "path",
            "table",
            "mode",
            "vector_count",
            "dimensions",
            "stored_min_dimensions",
            "stored_max_dimensions",
            "oldest_indexed_at",
            "newest_indexed_at",
        ):
            if key in stats:
                lines.append(f"  {key}: {_value(stats.get(key))}")
    dense = metadata.get("dense")
    if isinstance(dense, dict):
        lines.append("  dense:")
        for line in _index_metadata_lines(dense):
            lines.append(f"  {line}")
    lexical = metadata.get("lexical")
    if isinstance(lexical, dict):
        lines.append("  lexical:")
        for line in _index_metadata_lines(lexical):
            lines.append(f"  {line}")
    return lines


def _value(value: object) -> str:
    if value is None:
        return "-"
    return str(value)


def _truncate(value: str, limit: int) -> str:
    text = str(value).replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)] + "..."


def _health_from_stats(stats: DatabaseStats) -> MonitorHealth:
    issues: list[str] = []
    index_lag = None
    if stats.index_document_count is not None:
        index_lag = max(stats.unit_count - stats.index_document_count, 0)
        if index_lag > 0:
            issues.append("index_lag")
    if stats.unit_count < 0:
        issues.append("invalid_unit_count")
    if stats.pending_schema_migration_count > 0:
        issues.append("pending_schema_migrations")
    if stats.schema_version < stats.latest_schema_version:
        issues.append("schema_version_lag")
    return MonitorHealth(
        status="ok" if not issues else "degraded",
        index_lag=index_lag,
        issues=tuple(issues),
    )


def _issues(issues: tuple[str, ...]) -> str:
    if not issues:
        return "none"
    return ", ".join(issues)
