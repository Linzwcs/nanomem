from __future__ import annotations

from nanomem.config import NanoMemConfig, load_config
from nanomem.embeddings.base import EmbeddingModel
from nanomem.embeddings.hashing import HashingEmbeddingModel
from nanomem.embeddings.openai_compatible import OpenAICompatibleEmbeddingModel
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.heuristic import HeuristicMemoryUnitExtractor
from nanomem.extraction.llm import LLMMemoryUnitExtractor
from nanomem.index.base import MemoryUnitIndex
from nanomem.index.dense import DenseMemoryUnitIndex
from nanomem.index.hybrid import HybridMemoryUnitIndex
from nanomem.index.lexical import LexicalMemoryUnitIndex
from nanomem.service.core import NanoMemService
from nanomem.store.base import MemoryStore
from nanomem.store.sqlite import SQLiteMemoryUnitStore
from nanomem.control.service import NanoMemControlService
from nanomem.maintenance.service import NanoMemMaintenanceService


def service_from_config(config: NanoMemConfig) -> NanoMemService:
    return NanoMemService(
        store=store_from_config(config),
        index=index_from_config(config),
        extractor=extractor_from_config(config),
        default_recency_policy=config.read.default_recency_policy,
        default_max_units=config.read.default_max_units,
    )


def service_from_config_file(path: str) -> NanoMemService:
    return service_from_config(load_config(path))


def control_from_config(config: NanoMemConfig) -> NanoMemControlService:
    return NanoMemControlService(
        store=store_from_config(config),  # type: ignore[arg-type]
        index=index_from_config(config),
    )


def control_from_config_file(path: str) -> NanoMemControlService:
    return control_from_config(load_config(path))


def admin_from_config(config: NanoMemConfig) -> NanoMemControlService:
    return control_from_config(config)


def admin_from_config_file(path: str) -> NanoMemControlService:
    return control_from_config_file(path)


def maintenance_from_config(config: NanoMemConfig) -> NanoMemMaintenanceService:
    return NanoMemMaintenanceService(
        control=control_from_config(config),
        config=config.maintenance,
    )


def maintenance_from_config_file(path: str) -> NanoMemMaintenanceService:
    return maintenance_from_config(load_config(path))


def store_from_config(config: NanoMemConfig) -> MemoryStore:
    if config.store.backend != "sqlite":
        raise ValueError(f"Unsupported store backend: {config.store.backend}")
    return SQLiteMemoryUnitStore(config.store.path)


def index_from_config(config: NanoMemConfig) -> MemoryUnitIndex:
    backend = config.index.backend
    if backend == "lexical":
        return LexicalMemoryUnitIndex()
    if backend == "dense":
        return DenseMemoryUnitIndex(
            embedding_model=embedding_from_config(config),
            scan_limit=config.index.dense_scan_limit,
        )
    if backend == "hybrid":
        return HybridMemoryUnitIndex(
            lexical=LexicalMemoryUnitIndex(),
            dense=DenseMemoryUnitIndex(
                embedding_model=embedding_from_config(config),
                scan_limit=config.index.dense_scan_limit,
            ),
            lexical_weight=config.index.lexical_weight,
            dense_weight=config.index.dense_weight,
        )
    raise ValueError(f"Unsupported index backend: {backend}")


def embedding_from_config(config: NanoMemConfig) -> EmbeddingModel:
    embedding = config.index.embedding
    if embedding.backend == "hashing":
        return HashingEmbeddingModel(
            dimensions=embedding.dimensions,
            name=embedding.model,
        )
    if embedding.backend == "openai_compatible":
        if not embedding.model:
            raise ValueError("openai_compatible embedding requires model")
        return OpenAICompatibleEmbeddingModel(
            model=embedding.model,
            api_key=embedding.api_key,
            api_key_env=embedding.api_key_env,
            base_url=embedding.base_url,
        )
    raise ValueError(f"Unsupported embedding backend: {embedding.backend}")


def extractor_from_config(config: NanoMemConfig) -> MemoryUnitExtractor:
    extraction = config.extraction
    if extraction.backend == "heuristic":
        return HeuristicMemoryUnitExtractor()
    if extraction.backend == "llm":
        if not extraction.model:
            raise ValueError("llm extraction requires model")
        fallback = None
        if extraction.fallback_backend is None:
            fallback = None
        elif extraction.fallback_backend == "heuristic":
            fallback = HeuristicMemoryUnitExtractor()
        else:
            raise ValueError(
                "Unsupported extraction fallback backend: "
                f"{extraction.fallback_backend}"
            )
        return LLMMemoryUnitExtractor(
            model=extraction.model,
            api_key=extraction.api_key,
            api_key_env=extraction.api_key_env,
            base_url=extraction.base_url,
            fallback=fallback,
            confidence_threshold=extraction.confidence_threshold,
            strict_schema=extraction.strict_schema,
            max_messages_per_chunk=extraction.max_messages_per_chunk,
            max_chars_per_chunk=extraction.max_chars_per_chunk,
        )
    raise ValueError(f"Unsupported extraction backend: {extraction.backend}")
