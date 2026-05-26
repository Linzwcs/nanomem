from __future__ import annotations

import pytest

from nanomem.core.config import config_from_mapping
from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
)
from nanomem.control.service import NanoMemControlService, RetentionPolicy
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


def test_lancedb_startup_reindex_builds_from_sqlite_fact_store(tmp_path) -> None:
    store_path = tmp_path / "nanomem.db"
    source_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(store_path),
            },
            "index": {
                "backend": "dense",
            },
        }
    )
    source = service_from_config(source_config)
    try:
        _capture(
            source,
            content="I prefer concise Chinese answers.",
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        _capture(
            source,
            content="I want sidecar flow explanations before code.",
            occurred_at="2026-01-02T00:00:00+00:00",
        )
    finally:
        source.store.close()  # type: ignore[attr-defined]

    lancedb_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(store_path),
            },
            "index": {
                "backend": "lancedb",
                "path": str(tmp_path / "lancedb"),
                "rebuild_on_startup": True,
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 32,
                },
            },
        }
    )
    service = service_from_config(lancedb_config)
    try:
        assert service.index.document_count() == 2  # type: ignore[attr-defined]
        result = service.read(
            ReadRequest(
                owner_id="user-1",
                namespaces=("personal",),
                query="sidecar flow explanations",
                query_time="2026-01-03T00:00:00+00:00",
                max_units=3,
            )
        )
    finally:
        service.store.close()  # type: ignore[attr-defined]

    assert result.stats["index_backend"] == "lancedb_vector_v1"
    assert result.ranked_units[0].unit.text == (
        "I want sidecar flow explanations before code."
    )


def test_lancedb_retention_reindex_removes_deleted_units(tmp_path) -> None:
    config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(tmp_path / "nanomem.db"),
            },
            "index": {
                "backend": "lancedb",
                "path": str(tmp_path / "lancedb"),
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 32,
                },
            },
        }
    )
    service = service_from_config(config)
    try:
        _capture(
            service,
            content="I prefer old dashboard color choices.",
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        _capture(
            service,
            content="I prefer concise Chinese answers.",
            occurred_at="2026-01-03T00:00:00+00:00",
        )
        assert service.index.document_count() == 2  # type: ignore[attr-defined]

        control = NanoMemControlService(
            store=service.store,  # type: ignore[arg-type]
            index=service.index,
        )
        retention = control.retention_apply(
            RetentionPolicy(before="2026-01-02T00:00:00+00:00")
        )
        result = service.read(
            ReadRequest(
                owner_id="user-1",
                namespaces=("personal",),
                query="old dashboard color concise Chinese answers",
                query_time="2026-01-04T00:00:00+00:00",
                max_units=5,
            )
        )
    finally:
        service.store.close()  # type: ignore[attr-defined]

    assert retention.deleted_unit_count == 1
    assert retention.reindex.indexed_unit_count == 1
    assert result.context.unit_count == 1
    assert [ranked.unit.text for ranked in result.ranked_units] == [
        "I prefer concise Chinese answers."
    ]


def test_lancedb_metadata_mismatch_requires_reindex(tmp_path) -> None:
    store_path = tmp_path / "nanomem.db"
    index_path = tmp_path / "lancedb"
    initial_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(store_path),
            },
            "index": {
                "backend": "lancedb",
                "path": str(index_path),
                "rebuild_on_startup": False,
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 32,
                },
            },
        }
    )
    writer = service_from_config(initial_config)
    try:
        _capture(
            writer,
            content="I prefer concise Chinese answers.",
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        assert (index_path / "memory_units.index.json").exists()
    finally:
        writer.store.close()  # type: ignore[attr-defined]

    mismatched_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(store_path),
            },
            "index": {
                "backend": "lancedb",
                "path": str(index_path),
                "rebuild_on_startup": False,
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 64,
                },
            },
        }
    )
    mismatched = service_from_config(mismatched_config)
    try:
        with pytest.raises(ValueError, match="metadata mismatch"):
            mismatched.read(
                ReadRequest(
                    owner_id="user-1",
                    namespaces=("personal",),
                    query="concise Chinese answers",
                    query_time="2026-01-01T00:01:00+00:00",
                )
            )
    finally:
        mismatched.store.close()  # type: ignore[attr-defined]

    rebuild_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(store_path),
            },
            "index": {
                "backend": "lancedb",
                "path": str(index_path),
                "rebuild_on_startup": True,
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 64,
                },
            },
        }
    )
    rebuilt = service_from_config(rebuild_config)
    try:
        result = rebuilt.read(
            ReadRequest(
                owner_id="user-1",
                namespaces=("personal",),
                query="concise Chinese answers",
                query_time="2026-01-01T00:01:00+00:00",
            )
        )
    finally:
        rebuilt.store.close()  # type: ignore[attr-defined]

    assert result.ranked_units[0].unit.text == "I prefer concise Chinese answers."


def _capture(
    service,
    *,
    content: str,
    occurred_at: str,
) -> None:
    service.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=CaptureDialogue(
                occurred_at=occurred_at,
                messages=(
                    DialogueMessage(
                        role="user",
                        content=content,
                        timestamp=occurred_at,
                    ),
                ),
            ),
            capture_time=occurred_at,
        )
    )
