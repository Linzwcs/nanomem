from __future__ import annotations

from dataclasses import asdict, dataclass
from http import HTTPStatus
from importlib import resources
import json
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from nanomem.control.service import NanoMemControlService
from nanomem.contracts import (
    MemoryUnit,
    MemoryUnitSelector,
    OperationLogSelector,
    TimeRange,
)
from nanomem.serde import read_request_from_json, read_result_to_json
from nanomem.service.core import NanoMemService
from nanomem.time import now_utc_iso

_MANAGER_ASSET_PACKAGE = "nanomem.manager.assets"


@dataclass(frozen=True)
class ManagerResponse:
    status: HTTPStatus
    body: bytes
    content_type: str


def handle_manager_get(
    service: NanoMemService,
    path: str,
) -> ManagerResponse | None:
    parsed = urlparse(path)
    normalized_path = _normalized_control_path(parsed.path)
    if parsed.path in {"/admin", "/admin/", "/manager", "/manager/"}:
        return _asset_response("index.html")
    asset_name = _manager_asset_name(parsed.path)
    if asset_name is not None:
        return _asset_response(asset_name)
    if normalized_path is None:
        return None
    query = parse_qs(parsed.query, keep_blank_values=False)
    if normalized_path == "/manager/api/stats":
        return _json_response(_stats_payload(service))
    if normalized_path == "/manager/api/memory-units":
        return _json_response(_memory_units_payload(service, query))
    if normalized_path.startswith("/manager/api/memory-units/"):
        unit_id = unquote(normalized_path.removeprefix("/manager/api/memory-units/"))
        return _json_response(_memory_unit_payload(service, unit_id))
    if normalized_path.startswith("/manager/api/dialogues/"):
        dialogue_id = unquote(normalized_path.removeprefix("/manager/api/dialogues/"))
        return _json_response(_dialogue_payload(service, dialogue_id))
    if normalized_path == "/manager/api/operation-logs":
        return _json_response(_operation_logs_payload(service, query))
    return _json_response(
        {"error": "not_found", "path": normalized_path},
        status=HTTPStatus.NOT_FOUND,
    )


def handle_manager_post(
    service: NanoMemService,
    path: str,
    payload: dict[str, Any],
) -> ManagerResponse | None:
    parsed = urlparse(path)
    normalized_path = _normalized_control_path(parsed.path)
    if normalized_path is None:
        return None
    if normalized_path == "/manager/api/reindex":
        selector = _selector_from_payload(payload)
        return _json_response(asdict(service.reindex(selector)))
    if normalized_path == "/manager/api/retrieval-preview":
        request = read_request_from_json(_read_preview_payload(payload))
        result = service.read(request)
        return _json_response(read_result_to_json(result))
    return _json_response(
        {"error": "not_found", "path": normalized_path},
        status=HTTPStatus.NOT_FOUND,
    )


def _stats_payload(service: NanoMemService) -> dict[str, Any]:
    control = NanoMemControlService(
        store=service.store,  # type: ignore[arg-type]
        index=service.index,
    )
    return asdict(control.stats())


def _memory_units_payload(
    service: NanoMemService,
    query: dict[str, list[str]],
) -> dict[str, Any]:
    selector = _selector_from_query(query)
    units = service.store.query_units(selector)
    return {
        "selector": asdict(selector),
        "count": len(units),
        "units": [asdict(unit) for unit in units],
    }


def _memory_unit_payload(
    service: NanoMemService,
    unit_id: str,
) -> dict[str, Any]:
    units = service.store.get_units((unit_id,))
    if not units:
        raise KeyError(f"MemoryUnit not found: {unit_id}")
    unit = units[0]
    return {
        "unit": asdict(unit),
        "source_chunks": _source_chunks_payload(service, unit),
    }


def _dialogue_payload(
    service: NanoMemService,
    dialogue_id: str,
) -> dict[str, Any]:
    dialogue = service.store.get_dialogue(dialogue_id)
    if dialogue is None:
        raise KeyError(f"DialogueRecord not found: {dialogue_id}")
    produced_units = tuple(
        unit for unit in service.store.query_units(MemoryUnitSelector(limit=None))
        if any(ref.dialogue_id == dialogue_id for ref in unit.dialogue_refs)
    )
    return {
        "dialogue": asdict(dialogue),
        "produced_units": [asdict(unit) for unit in produced_units],
    }


def _source_chunks_payload(
    service: NanoMemService,
    unit: MemoryUnit,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for ref in unit.dialogue_refs:
        dialogue = service.store.get_dialogue(ref.dialogue_id)
        if dialogue is None:
            chunks.append(
                {
                    "ref": asdict(ref),
                    "dialogue": None,
                    "messages": [],
                    "status": "missing_dialogue",
                    "range_label": _range_label(ref.message_range),
                    "resolved_range": None,
                    "message_count": None,
                    "resolved_message_count": 0,
                    "raw_dialogue_available": False,
                    "requires_explicit_reveal": True,
                    "missing": True,
                }
            )
            continue
        resolved_range = _resolved_message_range(
            len(dialogue.messages),
            ref.message_range,
        )
        indices = range(resolved_range[0], resolved_range[1])
        messages = [
            {
                "index": index,
                "in_ref_range": True,
                **asdict(dialogue.messages[index]),
            }
            for index in indices
        ]
        dialogue_messages = [
            {
                "index": index,
                "in_ref_range": resolved_range[0] <= index < resolved_range[1],
                **asdict(message),
            }
            for index, message in enumerate(dialogue.messages)
        ]
        chunks.append(
            {
                "ref": asdict(ref),
                "dialogue": {
                    "dialogue_id": dialogue.dialogue_id,
                    "occurred_at": dialogue.occurred_at,
                    "captured_at": dialogue.captured_at,
                    "checksum": dialogue.checksum,
                    "metadata": dialogue.metadata,
                    "retention_until": dialogue.retention_until,
                    "redacted_at": dialogue.redacted_at,
                },
                "messages": messages,
                "dialogue_messages": dialogue_messages,
                "status": _source_chunk_status(
                    dialogue.redacted_at,
                    ref.message_range,
                    len(dialogue.messages),
                    resolved_range,
                ),
                "range_label": _range_label(ref.message_range),
                "resolved_range": resolved_range,
                "message_count": len(dialogue.messages),
                "resolved_message_count": len(messages),
                "raw_dialogue_available": dialogue.redacted_at is None,
                "requires_explicit_reveal": True,
                "missing": False,
            }
        )
    return chunks


def _resolved_message_range(
    message_count: int,
    message_range: tuple[int, int] | None,
) -> tuple[int, int]:
    if message_range is None:
        return 0, message_count
    start, end = message_range
    start = max(0, min(start, message_count))
    end = max(start, min(end, message_count))
    return start, end


def _range_label(message_range: tuple[int, int] | None) -> str:
    if message_range is None:
        return "whole dialogue"
    return f"messages [{message_range[0]}, {message_range[1]})"


def _source_chunk_status(
    redacted_at: str | None,
    message_range: tuple[int, int] | None,
    message_count: int,
    resolved_range: tuple[int, int],
) -> str:
    if redacted_at is not None:
        return "redacted_dialogue"
    if resolved_range[0] == resolved_range[1]:
        return "empty_range"
    if message_range is None:
        return "ok"
    start, end = message_range
    if start < 0 or end > message_count:
        return "out_of_range_clamped"
    return "ok"


def _operation_logs_payload(
    service: NanoMemService,
    query: dict[str, list[str]],
) -> dict[str, Any]:
    selector = OperationLogSelector(
        owner_id=_single(query, "owner_id"),
        namespaces=_namespaces(query),
        operation_type=_single(query, "operation_type"),
        status=_single(query, "status"),
        time_range=_time_range_from_query(query),
        limit=_limit(query, default=50),
    )
    logs = service.store.list_operation_logs(selector)
    return {
        "selector": asdict(selector),
        "count": len(logs),
        "logs": [asdict(log) for log in logs],
    }


def _selector_from_query(
    query: dict[str, list[str]],
) -> MemoryUnitSelector:
    return MemoryUnitSelector(
        owner_id=_single(query, "owner_id"),
        namespaces=_namespaces(query),
        time_range=_time_range_from_query(query),
        memory_types=tuple(_many(query, "memory_type")),
        include_redacted=_bool(_single(query, "include_redacted")),
        limit=_limit(query, default=50),
        order=_order(query),
    )


def _selector_from_payload(payload: dict[str, Any]) -> MemoryUnitSelector:
    namespaces = payload.get("namespaces")
    if namespaces is None and payload.get("namespace") is not None:
        namespaces = [payload.get("namespace")]
    return MemoryUnitSelector(
        owner_id=_optional_str(payload.get("owner_id")),
        namespaces=(
            None
            if namespaces is None
            else tuple(str(item) for item in _list(namespaces))
        ),
        time_range=_time_range_from_payload(payload.get("time_range")),
        memory_types=tuple(str(item) for item in _list(payload.get("memory_types"))),
        include_redacted=bool(payload.get("include_redacted", False)),
        limit=None,
    )


def _read_preview_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if not str(normalized.get("query_time") or "").strip():
        normalized["query_time"] = now_utc_iso()
    return normalized


def _time_range_from_query(
    query: dict[str, list[str]],
) -> TimeRange | None:
    start = _single(query, "start")
    end = _single(query, "end")
    if start is None and end is None:
        return None
    return TimeRange(start=start, end=end)


def _time_range_from_payload(value: Any) -> TimeRange | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("time_range must be an object")
    start = _optional_str(value.get("start"))
    end = _optional_str(value.get("end"))
    if start is None and end is None:
        return None
    return TimeRange(start=start, end=end)


def _single(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _many(query: dict[str, list[str]], key: str) -> tuple[str, ...]:
    values = query.get(key)
    if not values:
        return ()
    result: list[str] = []
    for value in values:
        for item in value.split(","):
            text = item.strip()
            if text:
                result.append(text)
    return tuple(result)


def _namespaces(query: dict[str, list[str]]) -> tuple[str, ...] | None:
    values = _many(query, "namespace") + _many(query, "namespaces")
    return values or None


def _limit(query: dict[str, list[str]], *, default: int) -> int | None:
    value = _single(query, "limit")
    if value is None:
        return default
    parsed = int(value)
    if parsed < 0:
        raise ValueError("limit must be non-negative")
    return min(parsed, 500)


def _order(query: dict[str, list[str]]) -> str:
    value = _single(query, "order")
    if value == "oldest_first":
        return "oldest_first"
    return "newest_first"


def _bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected list")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _json_response(
    payload: dict[str, Any],
    *,
    status: HTTPStatus = HTTPStatus.OK,
) -> ManagerResponse:
    return ManagerResponse(
        status=status,
        body=json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        content_type="application/json; charset=utf-8",
    )


def _asset_response(name: str) -> ManagerResponse:
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return _json_response(
            {"error": "not_found", "path": name},
            status=HTTPStatus.NOT_FOUND,
        )
    try:
        body = (
            resources.files(_MANAGER_ASSET_PACKAGE)
            .joinpath(name)
            .read_bytes()
        )
    except FileNotFoundError:
        return _json_response(
            {"error": "not_found", "path": name},
            status=HTTPStatus.NOT_FOUND,
        )
    return ManagerResponse(
        status=HTTPStatus.OK,
        body=body,
        content_type=_asset_content_type(name),
    )


def _asset_content_type(name: str) -> str:
    if name.endswith(".html"):
        return "text/html; charset=utf-8"
    if name.endswith(".css"):
        return "text/css; charset=utf-8"
    if name.endswith(".js"):
        return "text/javascript; charset=utf-8"
    return "application/octet-stream"


def _normalized_control_path(path: str) -> str | None:
    if path.startswith("/manager/api/"):
        return path
    if path.startswith("/admin/api/"):
        return "/manager/api/" + path.removeprefix("/admin/api/")
    return None


def _manager_asset_name(path: str) -> str | None:
    if path.startswith("/admin/assets/"):
        return path.removeprefix("/admin/assets/")
    if path.startswith("/manager/assets/"):
        return path.removeprefix("/manager/assets/")
    return None
