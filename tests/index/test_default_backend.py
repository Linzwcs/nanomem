from __future__ import annotations

from nanomem.config import config_from_mapping
from nanomem.factory import index_from_config
from nanomem.index.dense import DenseMemoryUnitIndex
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
