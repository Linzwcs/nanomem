from __future__ import annotations

from nanomem.control.service import NanoMemControlService
from nanomem.index.dense import DenseMemoryUnitIndex
from nanomem.service.facade import ControlFacade
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore


def test_control_facade_delegates_stats(tmp_path) -> None:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    control = NanoMemControlService(store=store, index=DenseMemoryUnitIndex())
    facade = ControlFacade(control)

    stats = facade.stats()

    assert stats.unit_count == 0
    assert stats.store == "sqlite"


def test_control_facade_does_not_expose_write_operations() -> None:
    # The facade is intentionally read-mostly. Hard-fail this test if a
    # write method gets accidentally added without explicit review.
    write_methods = {
        "backup",
        "export_json",
        "retention_apply",
        "operation_log_retention_apply",
        "reindex",
    }
    facade_methods = {
        name for name in dir(ControlFacade) if not name.startswith("_")
    }
    leaked = write_methods & facade_methods
    assert not leaked, (
        f"ControlFacade leaked write methods: {leaked}. "
        "Heavy admin actions stay on the CLI/control plane, not in the "
        "server-facing facade."
    )
