from __future__ import annotations

from dataclasses import asdict, replace

from nanomem.contracts import MemoryUnitSelector, ReindexResult
from nanomem.index.base import MemoryUnitIndex
from nanomem.store.base import MemoryStore


def rebuild_index(
    *,
    store: MemoryStore,
    index: MemoryUnitIndex,
    selector: MemoryUnitSelector | None = None,
) -> ReindexResult:
    selected = _selector_for_rebuild(selector)
    units = store.query_units(selected)
    index.clear()
    index.upsert(units)
    return ReindexResult(
        indexed_unit_count=len(units),
        index_backend=getattr(index, "name", type(index).__name__),
        stats={
            "selector": asdict(selected),
            "selector_filtered": _selector_is_filtered(selected),
        },
    )


def _selector_for_rebuild(
    selector: MemoryUnitSelector | None,
) -> MemoryUnitSelector:
    if selector is None:
        return MemoryUnitSelector(limit=None)
    if selector.limit is None and selector.offset == 0:
        return selector
    return replace(selector, limit=None, offset=0)


def _selector_is_filtered(selector: MemoryUnitSelector) -> bool:
    return any(
        (
            selector.owner_id is not None,
            selector.namespaces is not None,
            bool(selector.unit_ids),
            selector.time_range is not None,
            bool(selector.memory_types),
            selector.text_query is not None,
            selector.include_redacted,
        )
    )
