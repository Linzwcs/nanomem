from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = ".nanomem"
DEFAULT_SQLITE_FILENAME = "nanomem.db"


@dataclass(frozen=True)
class StoreConfig:
    backend: str = "sqlite"
    path: str = f"{DEFAULT_DATA_DIR}/{DEFAULT_SQLITE_FILENAME}"


@dataclass(frozen=True)
class EmbeddingConfig:
    backend: str = "hashing"
    model: str | None = None
    dimensions: int = 128
    base_url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None


@dataclass(frozen=True)
class IndexConfig:
    backend: str = "dense"
    path: str = f"{DEFAULT_DATA_DIR}/lancedb"
    table: str = "memory_units"
    distance_type: str = "cosine"
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    lexical_weight: float = 0.5
    dense_weight: float = 0.5
    dense_scan_limit: int = 2_000
    rebuild_on_startup: bool = True


@dataclass(frozen=True)
class ExtractionConfig:
    backend: str = "heuristic"
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    api_key_env: str | None = None
    fallback_backend: str | None = "heuristic"
    strict_schema: bool = True
    max_messages_per_chunk: int | None = 24
    max_chars_per_chunk: int | None = None


@dataclass(frozen=True)
class ReadConfig:
    default_recency_policy: str = "balanced"
    default_max_units: int = 10


@dataclass(frozen=True)
class RetentionConfig:
    enabled: bool = False
    before: str | None = None
    max_age_days: int | None = None


@dataclass(frozen=True)
class BackupConfig:
    enabled: bool = False
    path: str | None = None
    overwrite: bool = False


@dataclass(frozen=True)
class ExportConfig:
    enabled: bool = False
    path: str | None = None
    include_operation_logs: bool = True
    overwrite: bool = False


@dataclass(frozen=True)
class MaintenanceConfig:
    integrity_check: bool = True
    backup: BackupConfig = field(default_factory=BackupConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    operation_log_retention: RetentionConfig = field(default_factory=RetentionConfig)


@dataclass(frozen=True)
class NanoMemConfig:
    data_dir: str = DEFAULT_DATA_DIR
    store: StoreConfig = field(default_factory=StoreConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    read: ReadConfig = field(default_factory=ReadConfig)
    maintenance: MaintenanceConfig = field(default_factory=MaintenanceConfig)


def load_config(path: str | Path) -> NanoMemConfig:
    payload = load_config_payload(path)
    return config_from_mapping(payload)


def load_config_payload(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        value = json.loads(text)
    else:
        value = parse_simple_yaml(text)
    if not isinstance(value, dict):
        raise ValueError("NanoMem config root must be a mapping")
    return value


def config_from_mapping(payload: dict[str, Any]) -> NanoMemConfig:
    data_dir = str(payload.get("data_dir", DEFAULT_DATA_DIR))
    store_payload = _mapping(payload.get("store"))
    index_payload = _mapping(payload.get("index"))
    embedding_payload = _mapping(index_payload.get("embedding"))
    extraction_payload = _mapping(payload.get("extraction"))
    read_payload = _mapping(payload.get("read"))
    maintenance_payload = _mapping(payload.get("maintenance"))
    store_path = _optional_str(store_payload.get("path"))
    return NanoMemConfig(
        data_dir=data_dir,
        store=StoreConfig(
            backend=str(store_payload.get("backend", "sqlite")),
            path=store_path or _default_sqlite_path(data_dir),
        ),
        index=IndexConfig(
            backend=str(index_payload.get("backend", "dense")),
            path=str(index_payload.get("path", _default_index_path(data_dir))),
            table=str(index_payload.get("table", "memory_units")),
            distance_type=str(index_payload.get("distance_type", "cosine")),
            embedding=EmbeddingConfig(
                backend=str(embedding_payload.get("backend", "hashing")),
                model=_optional_str(embedding_payload.get("model")),
                dimensions=int(embedding_payload.get("dimensions", 128)),
                base_url=_optional_str(embedding_payload.get("base_url")),
                api_key=_optional_str(embedding_payload.get("api_key")),
                api_key_env=_optional_str(embedding_payload.get("api_key_env")),
            ),
            lexical_weight=float(index_payload.get("lexical_weight", 0.5)),
            dense_weight=float(index_payload.get("dense_weight", 0.5)),
            dense_scan_limit=int(index_payload.get("dense_scan_limit", 2_000)),
            rebuild_on_startup=_optional_bool(
                index_payload.get("rebuild_on_startup"),
                default=True,
            ),
        ),
        extraction=ExtractionConfig(
            backend=str(extraction_payload.get("backend", "heuristic")),
            model=_optional_str(extraction_payload.get("model")),
            base_url=_optional_str(extraction_payload.get("base_url")),
            api_key=_optional_str(extraction_payload.get("api_key")),
            api_key_env=_optional_str(extraction_payload.get("api_key_env")),
            fallback_backend=_optional_str(
                extraction_payload.get("fallback_backend", "heuristic")),
            strict_schema=_optional_bool(
                extraction_payload.get("strict_schema"),
                default=True,
            ),
            max_messages_per_chunk=_optional_int(
                extraction_payload.get("max_messages_per_chunk", 24)
            ),
            max_chars_per_chunk=_optional_int(
                extraction_payload.get("max_chars_per_chunk")
            ),
        ),
        read=ReadConfig(
            default_recency_policy=_recency_policy(
                read_payload.get("default_recency_policy", "balanced")),
            default_max_units=int(
                read_payload.get("default_max_units", 10)),
        ),
        maintenance=MaintenanceConfig(
            integrity_check=bool(
                maintenance_payload.get("integrity_check", True)),
            backup=BackupConfig(
                enabled=bool(
                    _mapping(maintenance_payload.get("backup")).get(
                        "enabled",
                        False,
                    )
                ),
                path=_optional_str(
                    _mapping(maintenance_payload.get("backup")).get("path")),
                overwrite=bool(
                    _mapping(maintenance_payload.get("backup")).get(
                        "overwrite",
                        False,
                    )
                ),
            ),
            export=ExportConfig(
                enabled=bool(
                    _mapping(maintenance_payload.get("export")).get(
                        "enabled",
                        False,
                    )
                ),
                path=_optional_str(
                    _mapping(maintenance_payload.get("export")).get("path")),
                include_operation_logs=bool(
                    _mapping(maintenance_payload.get("export")).get(
                        "include_operation_logs",
                        True,
                    )
                ),
                overwrite=bool(
                    _mapping(maintenance_payload.get("export")).get(
                        "overwrite",
                        False,
                    )
                ),
            ),
            retention=RetentionConfig(
                enabled=bool(
                    _mapping(maintenance_payload.get("retention")).get(
                        "enabled",
                        False,
                    )
                ),
                before=_optional_str(
                    _mapping(maintenance_payload.get("retention")).get(
                        "before",
                    )
                ),
                max_age_days=_optional_int(
                    _mapping(maintenance_payload.get("retention")).get(
                        "max_age_days",
                    )
                ),
            ),
            operation_log_retention=RetentionConfig(
                enabled=bool(
                    _mapping(
                        maintenance_payload.get("operation_log_retention")
                    ).get("enabled", False)
                ),
                before=_optional_str(
                    _mapping(
                        maintenance_payload.get("operation_log_retention")
                    ).get("before")
                ),
                max_age_days=_optional_int(
                    _mapping(
                        maintenance_payload.get("operation_log_retention")
                    ).get("max_age_days")
                ),
            ),
        ),
    )


def parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            raise ValueError(f"Unsupported YAML line: {raw_line}")
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(raw_value)
    return root


def _parse_scalar(value: str) -> Any:
    if value in {"null", "None", "~"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (
        (value.startswith('"') and value.endswith('"'))
        or (value.startswith("'") and value.endswith("'"))
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping, got {type(value).__name__}")
    return value


def _default_sqlite_path(data_dir: str) -> str:
    return str(Path(data_dir) / DEFAULT_SQLITE_FILENAME)


def _default_index_path(data_dir: str) -> str:
    return str(Path(data_dir) / "lancedb")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"Expected boolean, got {value!r}")


def _recency_policy(value: Any) -> str:
    text = str(value)
    if text not in {"recent", "balanced", "historical"}:
        raise ValueError(f"Unsupported read.default_recency_policy: {text}")
    return text
