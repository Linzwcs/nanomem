from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nanomem.core.contracts import IndexHit, IndexSearchRequest, MemoryUnit
from nanomem.core.errors import ConfigError
from nanomem.pipeline.retrieval.embeddings.base import EmbeddingModel
from nanomem.pipeline.retrieval.embeddings.hashing import HashingEmbeddingModel


class LanceDBMemoryUnitIndex:
    """Persistent LanceDB vector index for MemoryUnits.

    LanceDB stores only search-time duplicates. SQLite or another MemoryStore
    remains authoritative for the full MemoryUnit payload.
    """

    name = "lancedb_vector_v1"

    def __init__(
        self,
        path: str | Path,
        *,
        table_name: str = "memory_units",
        embedding_model: EmbeddingModel | None = None,
        dimensions: int | None = None,
        distance_type: str = "cosine",
    ) -> None:
        self.path = Path(path)
        self.table_name = table_name
        self.embedding_model = embedding_model or HashingEmbeddingModel()
        self.dimensions = dimensions or getattr(self.embedding_model, "dimensions", 128)
        self.distance_type = _normalized_distance_type(distance_type)
        self._metadata_path = self.path / _metadata_filename(self.table_name)
        self.path.mkdir(parents=True, exist_ok=True)
        self._db = _require_lancedb().connect(str(self.path))

    def clear(self) -> None:
        if self.table_name in _table_names(self._db):
            _drop_table(self._db, self.table_name)
        self._write_metadata()

    def document_count(self) -> int:
        table = self._table(create=False)
        if table is None:
            return 0
        return int(table.count_rows())

    def upsert(self, units: tuple[MemoryUnit, ...]) -> None:
        if not units:
            return
        self._ensure_metadata_compatible()
        table = self._table(create=True)
        assert table is not None
        rows = self._rows(units)
        table.delete(_where_in("unit_id", tuple(unit.unit_id for unit in units)))
        table.add(rows)

    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]:
        table = self._table(create=False)
        if table is None:
            return ()
        self._ensure_metadata_compatible()
        query_vector = list(self.embedding_model.embed((request.query,))[0])
        limit = request.limit or 20
        query = (
            table.search(query_vector, vector_column_name="vector")
            .distance_type(self.distance_type)
            .where(_search_filter(request))
            .limit(limit)
        )
        rows = query.to_list()
        hits = [
            IndexHit(
                unit_id=str(row["unit_id"]),
                score=_distance_to_score(
                    float(row.get("_distance", 0.0)),
                    distance_type=self.distance_type,
                ),
                retrieval_text=str(row.get("retrieval_text", "")),
                score_breakdown={
                    "lancedb_distance": row.get("_distance"),
                    "distance_type": self.distance_type,
                    "embedding_model": self.embedding_model.name,
                    "index_backend": self.name,
                },
            )
            for row in rows
        ]
        hits = [hit for hit in hits if hit.score > 0.0]
        hits.sort(key=lambda hit: (-hit.score, hit.unit_id))
        return tuple(hits[:limit])

    def delete(self, unit_ids: tuple[str, ...]) -> None:
        if not unit_ids:
            return
        table = self._table(create=False)
        if table is not None:
            self._ensure_metadata_compatible()
            table.delete(_where_in("unit_id", unit_ids))

    def _table(self, *, create: bool) -> Any | None:
        if self.table_name in _table_names(self._db):
            return self._db.open_table(self.table_name)
        if not create:
            return None
        self._write_metadata()
        return self._db.create_table(self.table_name, schema=_schema(self.dimensions))

    def _metadata(self) -> dict[str, Any]:
        return {
            "format_version": 1,
            "backend": self.name,
            "table_name": self.table_name,
            "embedding_model": self.embedding_model.name,
            "dimensions": self.dimensions,
            "distance_type": self.distance_type,
        }

    def _write_metadata(self) -> None:
        self._metadata_path.write_text(
            json.dumps(self._metadata(), sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def _ensure_metadata_compatible(self) -> None:
        if self.table_name not in _table_names(self._db):
            self._write_metadata()
            return
        if not self._metadata_path.exists():
            self._write_metadata()
            return
        stored = json.loads(self._metadata_path.read_text(encoding="utf-8"))
        expected = self._metadata()
        mismatches = {
            key: {"stored": stored.get(key), "expected": expected[key]}
            for key in ("backend", "embedding_model", "dimensions", "distance_type")
            if stored.get(key) != expected[key]
        }
        if mismatches:
            raise ConfigError(
                "LanceDB index metadata mismatch. Run reindex or clear the "
                f"index before using this configuration: {mismatches}"
            )

    def _rows(self, units: tuple[MemoryUnit, ...]) -> list[dict[str, Any]]:
        vectors = self.embedding_model.embed(tuple(unit.text for unit in units))
        rows: list[dict[str, Any]] = []
        for unit, vector in zip(units, vectors):
            namespace = unit.scope.namespace or ""
            timestamp = unit.timestamp or unit.available_at
            rows.append(
                {
                    "unit_id": unit.unit_id,
                    "owner_id": unit.scope.owner_id,
                    "namespace": namespace,
                    "timestamp": unit.timestamp,
                    "available_at": unit.available_at,
                    "sort_timestamp": timestamp,
                    "memory_type": unit.memory_type,
                    "redacted_at": unit.redacted_at or "",
                    "embedding_model": self.embedding_model.name,
                    "retrieval_text": unit.text,
                    "metadata_json": json.dumps(
                        unit.metadata,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "vector": [float(value) for value in vector],
                }
            )
        return rows


def _require_lancedb() -> Any:
    try:
        import lancedb
    except ImportError as exc:
        raise ImportError(
            "LanceDB index backend requires the optional dependency. "
            "Install NanoMem with the 'lancedb' extra."
        ) from exc
    return lancedb


def _table_names(db: Any) -> set[str]:
    if hasattr(db, "list_tables"):
        response = db.list_tables()
        names = response.tables if hasattr(response, "tables") else response
        return set(str(name) for name in names)
    return set(str(name) for name in db.table_names())


def _drop_table(db: Any, table_name: str) -> None:
    if hasattr(db, "drop_table"):
        db.drop_table(table_name)
        return
    db.open_table(table_name).delete("unit_id IS NOT NULL")


def _metadata_filename(table_name: str) -> str:
    safe = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in table_name
    ).strip("._")
    return f"{safe or 'memory_units'}.index.json"


def _schema(dimensions: int) -> Any:
    try:
        import pyarrow as pa
    except ImportError as exc:
        raise ImportError(
            "LanceDB index backend requires pyarrow from the 'lancedb' extra."
        ) from exc
    return pa.schema(
        [
            pa.field("unit_id", pa.string(), nullable=False),
            pa.field("owner_id", pa.string(), nullable=False),
            pa.field("namespace", pa.string(), nullable=False),
            pa.field("timestamp", pa.string(), nullable=False),
            pa.field("available_at", pa.string(), nullable=False),
            pa.field("sort_timestamp", pa.string(), nullable=False),
            pa.field("memory_type", pa.string(), nullable=False),
            pa.field("redacted_at", pa.string(), nullable=False),
            pa.field("embedding_model", pa.string(), nullable=False),
            pa.field("retrieval_text", pa.string(), nullable=False),
            pa.field("metadata_json", pa.string(), nullable=False),
            pa.field("vector", pa.list_(pa.float32(), dimensions), nullable=False),
        ]
    )


def _search_filter(request: IndexSearchRequest) -> str:
    clauses = [
        f"owner_id = {_sql_literal(request.owner_id)}",
        "redacted_at = ''",
    ]
    if request.namespaces is not None:
        if not request.namespaces:
            return "false"
        clauses.append(_where_in("namespace", request.namespaces))
    if request.time_range is not None:
        if request.time_range.start is not None:
            clauses.append(f"sort_timestamp >= {_sql_literal(request.time_range.start)}")
        if request.time_range.end is not None:
            clauses.append(f"sort_timestamp <= {_sql_literal(request.time_range.end)}")
    return " AND ".join(f"({clause})" for clause in clauses)


def _where_in(column: str, values: tuple[str, ...]) -> str:
    if not values:
        return "false"
    return f"{column} IN ({', '.join(_sql_literal(value) for value in values)})"


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _normalized_distance_type(value: str) -> str:
    text = value.strip().lower()
    if text not in {"cosine", "l2", "dot"}:
        raise ConfigError(f"Unsupported LanceDB distance_type: {value}")
    return text


def _distance_to_score(distance: float, *, distance_type: str) -> float:
    if distance_type == "cosine":
        return max(0.0, 1.0 - distance)
    if distance_type == "l2":
        return 1.0 / (1.0 + max(0.0, distance))
    return max(0.0, -distance)
