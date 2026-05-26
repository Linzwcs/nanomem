from __future__ import annotations

from pathlib import Path

from nanomem.pipeline.retrieval.embeddings.base import EmbeddingModel
from nanomem.pipeline.retrieval.embeddings.cache import CachedEmbeddingModel
from nanomem.pipeline.retrieval.embeddings.hashing import HashingEmbeddingModel


class _CountingEmbeddingModel:
    """Test double counting how many times embed() is called."""

    name = "counting_v1"

    def __init__(self, dimensions: int = 4) -> None:
        self.dimensions = dimensions
        self.call_count = 0
        self.text_count = 0

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.call_count += 1
        self.text_count += len(texts)
        # Deterministic so we can verify identity on cache hit.
        return tuple(
            tuple(float(i + len(t)) for i in range(self.dimensions)) for t in texts
        )


def test_cache_satisfies_embedding_model_protocol(tmp_path) -> None:
    inner = HashingEmbeddingModel(dimensions=16)
    cached: EmbeddingModel = CachedEmbeddingModel(inner, path=tmp_path / "cache.db")
    vectors = cached.embed(("hello",))
    assert len(vectors) == 1
    assert len(vectors[0]) == 16
    assert cached.name == inner.name


def test_repeated_calls_hit_cache(tmp_path) -> None:
    inner = _CountingEmbeddingModel()
    cached = CachedEmbeddingModel(inner, path=tmp_path / "cache.db")

    cached.embed(("hello", "world"))
    assert inner.call_count == 1
    assert inner.text_count == 2

    cached.embed(("hello", "world"))
    # No additional underlying calls — fully served from cache.
    assert inner.call_count == 1
    assert inner.text_count == 2

    stats = cached.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 2
    assert stats["rows"] == 2


def test_mixed_hit_and_miss_batches_only_missing(tmp_path) -> None:
    inner = _CountingEmbeddingModel()
    cached = CachedEmbeddingModel(inner, path=tmp_path / "cache.db")

    cached.embed(("a",))
    assert inner.text_count == 1

    cached.embed(("a", "b", "c"))
    # "a" served from cache, "b" + "c" embedded fresh.
    assert inner.text_count == 3  # 1 + 2 new


def test_cache_preserves_input_order(tmp_path) -> None:
    inner = _CountingEmbeddingModel(dimensions=2)
    cached = CachedEmbeddingModel(inner, path=tmp_path / "cache.db")

    first = cached.embed(("apple", "banana", "cherry"))
    second = cached.embed(("cherry", "apple", "banana"))

    # second result must match the requested order
    assert second[0] == first[2]  # cherry
    assert second[1] == first[0]  # apple
    assert second[2] == first[1]  # banana


def test_cache_persists_across_instances(tmp_path) -> None:
    inner1 = _CountingEmbeddingModel()
    cached1 = CachedEmbeddingModel(inner1, path=tmp_path / "cache.db")
    cached1.embed(("persistent",))
    cached1.close()

    inner2 = _CountingEmbeddingModel()
    cached2 = CachedEmbeddingModel(inner2, path=tmp_path / "cache.db")
    cached2.embed(("persistent",))

    # Second instance never invoked its underlying model.
    assert inner2.call_count == 0


def test_different_model_names_do_not_collide(tmp_path) -> None:
    class _Model:
        def __init__(self, name: str) -> None:
            self.name = name

        def embed(self, texts):
            return tuple((1.0, 2.0, 3.0) for _ in texts)

    cached_a = CachedEmbeddingModel(_Model("model-a"), path=tmp_path / "cache.db")
    cached_b = CachedEmbeddingModel(_Model("model-b"), path=tmp_path / "cache.db")

    cached_a.embed(("shared text",))
    cached_b.embed(("shared text",))

    # Both should have populated independent rows.
    assert cached_a.stats()["rows"] == 1
    assert cached_b.stats()["rows"] == 1


def test_empty_input_returns_empty(tmp_path) -> None:
    inner = _CountingEmbeddingModel()
    cached = CachedEmbeddingModel(inner, path=tmp_path / "cache.db")
    assert cached.embed(()) == ()
    assert inner.call_count == 0


def test_cache_handles_unicode(tmp_path) -> None:
    inner = HashingEmbeddingModel(dimensions=8)
    cached = CachedEmbeddingModel(inner, path=tmp_path / "cache.db")
    first = cached.embed(("你好世界",))
    second = cached.embed(("你好世界",))
    assert first == second
    assert cached.stats()["misses"] == 1
    assert cached.stats()["hits"] == 1


def test_cache_creates_parent_directories(tmp_path) -> None:
    nested_path = tmp_path / "nested" / "subdir" / "cache.db"
    inner = _CountingEmbeddingModel()
    cached = CachedEmbeddingModel(inner, path=nested_path)
    cached.embed(("hello",))
    assert nested_path.exists()
