from __future__ import annotations

import importlib.util

import pytest

from nanomem.core.config import config_from_mapping
from nanomem.factory import index_from_config
from nanomem.pipeline.retrieval.indexes.dense import DenseMemoryUnitIndex
from nanomem.service.core import NanoMemService


def test_default_config_uses_dense_embedding_retrieval() -> None:
    config = config_from_mapping({})

    assert config.index.backend == "dense"
    assert config.index.embedding.backend == "hashing"
    assert isinstance(index_from_config(config), DenseMemoryUnitIndex)


def test_default_service_uses_dense_embedding_retrieval() -> None:
    service = NanoMemService()

    assert isinstance(service.index, DenseMemoryUnitIndex)


def test_explicit_lexical_backend_remains_supported() -> None:
    config = config_from_mapping({"index": {"backend": "lexical"}})

    assert config.index.backend == "lexical"
    assert not isinstance(index_from_config(config), DenseMemoryUnitIndex)


def test_lancedb_index_config_parses_local_path_and_table(tmp_path) -> None:
    config = config_from_mapping(
        {
            "index": {
                "backend": "lancedb",
                "path": str(tmp_path / "vectors"),
                "table": "facts",
                "distance_type": "cosine",
                "embedding": {
                    "backend": "hashing",
                    "dimensions": 32,
                },
            }
        }
    )

    assert config.index.backend == "lancedb"
    assert config.index.path == str(tmp_path / "vectors")
    assert config.index.table == "facts"
    assert config.index.distance_type == "cosine"
    assert config.index.embedding.dimensions == 32


def test_lancedb_backend_reports_missing_optional_dependency(tmp_path) -> None:
    if importlib.util.find_spec("lancedb") is not None:
        pytest.skip("lancedb is installed in this environment")
    config = config_from_mapping(
        {
            "index": {
                "backend": "lancedb",
                "path": str(tmp_path / "vectors"),
            }
        }
    )

    with pytest.raises(ImportError, match="lancedb"):
        index_from_config(config)
