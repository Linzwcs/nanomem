from __future__ import annotations

import pytest

from nanomem.config import config_from_mapping
from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
)
from nanomem.factory import service_from_config

pytest.importorskip("lancedb")


def test_lancedb_index_persists_across_service_restart(tmp_path) -> None:
    config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(tmp_path / "nanomem.db"),
            },
            "index": {
                "backend": "lancedb",
                "path": str(tmp_path / "lancedb"),
                "table": "memory_units",
                "rebuild_on_startup": False,
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 32,
                },
            },
        }
    )
    writer = service_from_config(config)
    writer.capture(
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

    assert writer.index.document_count() == 1  # type: ignore[attr-defined]
    writer.store.close()  # type: ignore[attr-defined]

    reader = service_from_config(config)

    assert reader.index.document_count() == 1  # type: ignore[attr-defined]
    result = reader.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise Chinese answers",
            query_time="2026-01-01T00:01:00+00:00",
            max_units=3,
        )
    )

    assert result.stats["index_backend"] == "lancedb_vector_v1"
    assert result.ranked_units[0].unit.text == "I prefer concise Chinese answers."
    assert result.ranked_units[0].unit.scope.owner_id == "user-1"
    reader.store.close()  # type: ignore[attr-defined]
