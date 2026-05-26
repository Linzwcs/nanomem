from __future__ import annotations

from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    MemoryUnitSelector,
    ReadRequest,
)
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.service.core import NanoMemService
from nanomem.pipeline.storage.sqlite import SQLiteMemoryUnitStore


def test_service_reindex_rebuilds_active_index_from_store(tmp_path) -> None:
    db_path = tmp_path / "nanomem.db"
    store = SQLiteMemoryUnitStore(db_path)
    try:
        service = NanoMemService(store=store, index=DenseMemoryUnitIndex())
        service.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                dialogue=CaptureDialogue(
                    occurred_at="2026-01-01T00:00:00+00:00",
                    messages=(
                        DialogueMessage(
                            role="user",
                            content="I prefer concise Chinese answers.",
                            timestamp="2026-01-01T00:00:00+00:00",
                        ),
                    ),
                ),
                capture_time="2026-01-01T00:00:01+00:00",
            )
        )
    finally:
        store.close()

    reopened_store = SQLiteMemoryUnitStore(db_path)
    try:
        reopened_index = DenseMemoryUnitIndex()
        reopened_service = NanoMemService(
            store=reopened_store,
            index=reopened_index,
        )

        assert reopened_index.document_count() == 0

        result = reopened_service.reindex()

        assert result.indexed_unit_count == 1
        assert result.index_backend == "dense_cosine_v1"
        assert result.stats["selector_filtered"] is False
        assert reopened_index.document_count() == 1

        read = reopened_service.read(
            ReadRequest(
                owner_id="user-1",
                namespaces=None,
                query="concise Chinese answers",
                query_time="2026-01-02T00:00:00+00:00",
            )
        )
        assert len(read.ranked_units) == 1
    finally:
        reopened_store.close()


def test_service_reindex_can_filter_selected_units(tmp_path) -> None:
    store = SQLiteMemoryUnitStore(tmp_path / "nanomem.db")
    try:
        service = NanoMemService(store=store, index=DenseMemoryUnitIndex())
        for namespace, content in (
            ("personal", "I prefer concise Chinese answers."),
            ("work", "I prefer fact-level memory units for NanoMem."),
        ):
            service.capture(
                CaptureRequest(
                    scope=MemoryScope(owner_id="user-1", namespace=namespace),
                    dialogue=CaptureDialogue(
                        occurred_at="2026-01-01T00:00:00+00:00",
                        messages=(
                            DialogueMessage(
                                role="user",
                                content=content,
                                timestamp="2026-01-01T00:00:00+00:00",
                            ),
                        ),
                    ),
                    capture_time="2026-01-01T00:00:01+00:00",
                )
            )

        result = service.reindex(
            MemoryUnitSelector(
                owner_id="user-1",
                namespaces=("work",),
            )
        )

        assert result.indexed_unit_count == 1
        assert result.stats["selector_filtered"] is True

        read = service.read(
            ReadRequest(
                owner_id="user-1",
                namespaces=None,
                query="fact-level memory units",
                query_time="2026-01-02T00:00:00+00:00",
            )
        )
        assert len(read.ranked_units) == 1
        assert read.ranked_units[0].unit.scope.namespace == "work"
    finally:
        store.close()
