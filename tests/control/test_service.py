from __future__ import annotations

from nanomem.core.contracts import (
    DialogueRef,
    MemoryScope,
    MemoryUnit,
)
from nanomem.service.control.service import (
    NanoMemControlService,
    RetentionPolicy,
)
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore


def _make_control(tmp_path) -> NanoMemControlService:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    return NanoMemControlService(store=store, index=DenseMemoryUnitIndex())


def _unit(unit_id: str, timestamp: str) -> MemoryUnit:
    return MemoryUnit(
        unit_id=unit_id,
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        text=f"fact {unit_id}",
        memory_type="background",
        timestamp=timestamp,
        available_at=timestamp,
        dialogue_refs=(DialogueRef(dialogue_id="dlg-1"),),
    )


def test_stats_reports_zero_units_on_empty_store(tmp_path) -> None:
    control = _make_control(tmp_path)

    stats = control.stats()

    assert stats.unit_count == 0
    assert stats.active_unit_count == 0
    assert stats.dialogue_count == 0
    assert stats.index_health in {"synced", "unknown"}


def test_stats_reflects_appended_unit(tmp_path) -> None:
    control = _make_control(tmp_path)
    control.store.append_units((_unit("u-1", "2026-01-01T00:00:00+00:00"),))

    stats = control.stats()

    assert stats.unit_count == 1
    assert stats.active_unit_count == 1


def test_list_units_returns_appended_unit(tmp_path) -> None:
    control = _make_control(tmp_path)
    control.store.append_units((_unit("u-1", "2026-01-01T00:00:00+00:00"),))

    units = control.list_units(limit=10)

    assert len(units) == 1
    assert units[0].unit_id == "u-1"


def test_schema_status_on_fresh_store_has_no_pending_migrations(tmp_path) -> None:
    control = _make_control(tmp_path)

    status = control.schema_status()

    assert status.needs_migration is False
    assert status.pending == ()


def test_integrity_check_passes_on_fresh_store(tmp_path) -> None:
    control = _make_control(tmp_path)

    result = control.integrity_check()

    assert result.ok is True


def test_retention_preview_matches_old_units(tmp_path) -> None:
    control = _make_control(tmp_path)
    control.store.append_units(
        (
            _unit("old-1", "2024-01-01T00:00:00+00:00"),
            _unit("new-1", "2026-06-01T00:00:00+00:00"),
        )
    )

    preview = control.retention_preview(
        RetentionPolicy(before="2025-01-01T00:00:00+00:00")
    )

    assert preview.matched_unit_count == 1
    assert preview.sample_units[0].unit_id == "old-1"
