"""On-disk embedding cache.

Wraps any :class:`EmbeddingModel` with a persistent, content-addressed
cache so repeated calls for the same text return immediately without
re-invoking the underlying model. Essential for running benchmarks or
production pipelines that call ``embed()`` thousands of times against
the same text corpus.

Cache key: ``(model_name, sha256(text))``. The model name is part of
the key so multiple models can share the same cache file without
collision.

Backend: sqlite single-file database with one ``embeddings`` table.
Single-writer at a time (sqlite default); WAL is not enabled by
default to keep the disk layout dependency-free.

Vector serialization: compact ``struct.pack`` of ``float64`` values
(8 bytes per dimension). A 1024-dim embedding takes 8 KiB on disk.
"""

from __future__ import annotations

import hashlib
import sqlite3
import struct
import threading
from pathlib import Path

from nanomem.pipeline.retrieval.embeddings.base import EmbeddingModel


_SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    model_name TEXT NOT NULL,
    text_hash  TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector     BLOB    NOT NULL,
    created_at TEXT    NOT NULL,
    PRIMARY KEY (model_name, text_hash)
);
"""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pack_vector(vector: tuple[float, ...]) -> bytes:
    return struct.pack(f"<{len(vector)}d", *vector)


def _unpack_vector(blob: bytes, dimensions: int) -> tuple[float, ...]:
    return struct.unpack(f"<{dimensions}d", blob)


class CachedEmbeddingModel:
    """Embedding model wrapper with sqlite-backed on-disk cache.

    Drop-in for any :class:`EmbeddingModel`. The wrapped model is only
    called on cache misses. Use ``stats()`` to inspect hit / miss
    counts during a session.

    Concurrency: safe within a single process via an internal
    threading.Lock + sqlite's own locking. For multi-process use, sqlite
    busy-timeout handles the contention (set to 5s by default).

    Parameters
    ----------
    wrapped:
        The underlying embedding model. Its ``name`` becomes part of
        the cache key.
    path:
        sqlite database file path. Created with parents if missing.
    """

    def __init__(
        self,
        wrapped: EmbeddingModel,
        *,
        path: str | Path,
    ) -> None:
        self._wrapped = wrapped
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection: sqlite3.Connection | None = None
        self._hits = 0
        self._misses = 0

    @property
    def name(self) -> str:
        return self._wrapped.name

    @property
    def wrapped(self) -> EmbeddingModel:
        return self._wrapped

    @property
    def path(self) -> Path:
        return self._path

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        with self._lock:
            conn = self._ensure_connection()

            # Look up every text in one round trip.
            hashes = [_hash_text(text) for text in texts]
            placeholders = ",".join("?" * len(hashes))
            rows = conn.execute(
                f"SELECT text_hash, dimensions, vector FROM embeddings "
                f"WHERE model_name = ? AND text_hash IN ({placeholders})",
                (self._wrapped.name, *hashes),
            ).fetchall()
            cached: dict[str, tuple[float, ...]] = {
                row[0]: _unpack_vector(row[2], row[1]) for row in rows
            }

            missing_indexes: list[int] = []
            missing_texts: list[str] = []
            for index, (text, text_hash) in enumerate(zip(texts, hashes)):
                if text_hash not in cached:
                    missing_indexes.append(index)
                    missing_texts.append(text)

            self._hits += len(texts) - len(missing_texts)
            self._misses += len(missing_texts)

            # Cache miss path: call the wrapped model and persist.
            new_vectors: tuple[tuple[float, ...], ...] = ()
            if missing_texts:
                new_vectors = self._wrapped.embed(tuple(missing_texts))
                from nanomem.core.time import now_utc_iso

                now = now_utc_iso()
                conn.executemany(
                    "INSERT OR REPLACE INTO embeddings "
                    "(model_name, text_hash, dimensions, vector, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (
                            self._wrapped.name,
                            hashes[idx],
                            len(vector),
                            _pack_vector(vector),
                            now,
                        )
                        for idx, vector in zip(missing_indexes, new_vectors)
                    ],
                )
                conn.commit()
                for idx, vector in zip(missing_indexes, new_vectors):
                    cached[hashes[idx]] = vector

            return tuple(cached[text_hash] for text_hash in hashes)

    def stats(self) -> dict[str, int]:
        with self._lock:
            conn = self._ensure_connection()
            (size,) = conn.execute(
                "SELECT COUNT(*) FROM embeddings WHERE model_name = ?",
                (self._wrapped.name,),
            ).fetchone()
        return {
            "hits": self._hits,
            "misses": self._misses,
            "rows": int(size),
        }

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self._path),
                timeout=5.0,
                check_same_thread=False,
            )
            self._connection.executescript(_SCHEMA)
            self._connection.commit()
        return self._connection


__all__ = ["CachedEmbeddingModel"]
