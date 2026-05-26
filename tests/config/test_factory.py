from __future__ import annotations

import pytest

from nanomem.core.config import config_from_mapping, load_config
from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
)
from nanomem.pipeline.representation.llm import LLMMemoryUnitExtractor
from nanomem.factory import (
    embedding_from_config,
    extractor_from_config,
    service_from_config,
)


def test_developer_preview_defaults_resolve_under_data_dir() -> None:
    config = config_from_mapping({"data_dir": ".nanomem"})

    assert config.store.backend == "sqlite"
    assert config.store.path == ".nanomem/nanomem.db"
    assert config.index.backend == "dense"
    assert config.index.path == ".nanomem/lancedb"
    assert config.index.embedding.backend == "hashing"
    assert config.index.embedding.dimensions == 128
    assert config.index.rebuild_on_startup is True
    assert config.extraction.backend == "heuristic"
    assert config.extraction.max_dialogue_tokens == 512
    assert config.read.default_recency_policy == "balanced"
    assert config.read.default_max_units == 10


def test_developer_preview_yaml_config_matches_documented_minimal_shape(
    tmp_path,
) -> None:
    config_path = tmp_path / "nanomem.yaml"
    config_path.write_text(
        """
data_dir: .nanomem
store:
  backend: sqlite
index:
  backend: dense
extraction:
  backend: heuristic
read:
  default_recency_policy: balanced
  default_max_units: 10
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.store.path == ".nanomem/nanomem.db"
    assert config.index.backend == "dense"
    assert config.index.path == ".nanomem/lancedb"
    assert config.extraction.backend == "heuristic"
    assert config.extraction.max_dialogue_tokens == 512


def test_lancedb_config_keeps_sqlite_as_fact_store() -> None:
    config = config_from_mapping(
        {
            "data_dir": ".nanomem",
            "store": {"backend": "sqlite"},
            "index": {
                "backend": "lancedb",
                "path": ".nanomem/lancedb",
                "table": "memory_units",
                "distance_type": "cosine",
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 128,
                },
            },
        }
    )

    assert config.store.backend == "sqlite"
    assert config.store.path == ".nanomem/nanomem.db"
    assert config.index.backend == "lancedb"
    assert config.index.path == ".nanomem/lancedb"
    assert config.index.table == "memory_units"
    assert config.index.distance_type == "cosine"


def test_openai_compatible_embedding_config_requires_model() -> None:
    config = config_from_mapping(
        {
            "index": {
                "embedding": {
                    "backend": "openai_compatible",
                }
            }
        }
    )

    with pytest.raises(ValueError, match="openai_compatible embedding requires model"):
        embedding_from_config(config)


def test_llm_extraction_config_requires_model() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
            }
        }
    )

    with pytest.raises(ValueError, match="llm extraction requires model"):
        extractor_from_config(config)


def test_llm_extraction_config_builds_extractor_options() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
                "model": "test-model",
                "fallback_backend": "heuristic",
                "strict_schema": False,
                "max_messages_per_chunk": 6,
                "max_chars_per_chunk": 2000,
            }
        }
    )

    extractor = extractor_from_config(config)

    assert isinstance(extractor, LLMMemoryUnitExtractor)
    assert extractor.strict_schema is False
    assert extractor.max_messages_per_chunk == 6
    assert extractor.max_chars_per_chunk == 2000
    assert extractor.fallback is not None


def test_extraction_config_parses_dialogue_window_limit() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "heuristic",
                "max_dialogue_tokens": 256,
            }
        }
    )

    assert config.extraction.max_dialogue_tokens == 256


def test_llm_extraction_config_rejects_unknown_fallback_backend() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
                "model": "test-model",
                "fallback_backend": "other",
            }
        }
    )

    with pytest.raises(ValueError, match="Unsupported extraction fallback backend"):
        extractor_from_config(config)


def test_llm_extraction_config_parses_strict_schema_string_false() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
                "model": "test-model",
                "strict_schema": "false",
            }
        }
    )

    assert config.extraction.strict_schema is False


def test_service_from_config_rebuilds_index_from_sqlite_on_startup(tmp_path) -> None:
    db_path = tmp_path / "nanomem.db"
    config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(db_path),
            },
            "index": {
                "backend": "dense",
                "rebuild_on_startup": True,
            },
        }
    )
    first = service_from_config(config)
    first.capture(
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
    first.store.close()  # type: ignore[attr-defined]

    second = service_from_config(config)

    assert second.index.document_count() == 1  # type: ignore[attr-defined]
    second.store.close()  # type: ignore[attr-defined]


def test_service_from_config_can_skip_startup_reindex(tmp_path) -> None:
    db_path = tmp_path / "nanomem.db"
    writer_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(db_path),
            },
            "index": {
                "backend": "dense",
                "rebuild_on_startup": True,
            },
        }
    )
    writer = service_from_config(writer_config)
    writer.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=CaptureDialogue(
                occurred_at="2026-01-01T00:00:00+00:00",
                messages=(
                    DialogueMessage(
                        role="user",
                        content="I prefer Markdown bullet points.",
                        timestamp="2026-01-01T00:00:00+00:00",
                    ),
                ),
            ),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )
    writer.store.close()  # type: ignore[attr-defined]
    reader_config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(db_path),
            },
            "index": {
                "backend": "dense",
                "rebuild_on_startup": False,
            },
        }
    )

    reader = service_from_config(reader_config)

    assert reader.index.document_count() == 0  # type: ignore[attr-defined]
    reader.store.close()  # type: ignore[attr-defined]
