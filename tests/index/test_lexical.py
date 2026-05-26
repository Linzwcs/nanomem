from __future__ import annotations

from nanomem.core.contracts import IndexSearchRequest, MemoryScope, MemoryUnit
from nanomem.pipeline.retrieval.indexes.lexical import LexicalMemoryUnitIndex


def test_lexical_index_clear_removes_owner_index_entries() -> None:
    index = LexicalMemoryUnitIndex()
    index.upsert(
        (
            MemoryUnit(
                unit_id="unit-1",
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                text="The user prefers concise Chinese answers.",
                memory_type="preference",
                timestamp="2026-01-01T00:00:00+00:00",
                available_at="2026-01-01T00:00:01+00:00",
            ),
        )
    )

    assert index.search(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=None,
            query="concise Chinese answers",
        )
    )

    index.clear()

    assert index.document_count() == 0
    assert index.search(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=None,
            query="concise Chinese answers",
        )
    ) == ()
