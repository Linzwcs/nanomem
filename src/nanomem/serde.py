from __future__ import annotations

from dataclasses import asdict
from typing import Any

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    CaptureResult,
    CaptureSkip,
    DialogueMessage,
    DialogueRef,
    MemoryScope,
    MemoryUnit,
    PackedContext,
    RankedMemoryUnit,
    ReadRequest,
    ReadResult,
    TimeRange,
)


def capture_request_to_json(request: CaptureRequest) -> dict[str, Any]:
    return asdict(request)


def read_request_to_json(request: ReadRequest) -> dict[str, Any]:
    return asdict(request)


def capture_result_to_json(result: CaptureResult) -> dict[str, Any]:
    return asdict(result)


def read_result_to_json(result: ReadResult) -> dict[str, Any]:
    return asdict(result)


def capture_request_from_json(payload: dict[str, Any]) -> CaptureRequest:
    return CaptureRequest(
        scope=memory_scope_from_json(payload.get("scope")),
        dialogue=capture_dialogue_from_json(payload),
        capture_time=str(payload.get("capture_time", "")),
    )


def read_request_from_json(payload: dict[str, Any]) -> ReadRequest:
    scope_payload = _mapping(payload.get("scope"))
    owner_id = str(payload.get("owner_id") or scope_payload.get("owner_id")
                   or scope_payload.get("user_id") or "")
    namespaces = payload.get("namespaces")
    if namespaces is None and scope_payload.get("namespace") is not None:
        namespaces = [scope_payload.get("namespace")]
    return ReadRequest(
        owner_id=owner_id,
        namespaces=None if namespaces is None else tuple(str(item) for item in _list(namespaces)),
        query=_query(payload.get("query", "")),
        query_time=str(payload.get("query_time", "")),
        time_range=time_range_from_json(payload.get("time_range")),
        recency_policy=_optional_recency_policy(payload.get("recency_policy")),
        max_units=_optional_int(payload.get("max_units")),
        context_budget_tokens=_optional_int(payload.get("context_budget_tokens")),
        metadata=_mapping(payload.get("metadata")),
    )


def capture_result_from_json(payload: dict[str, Any]) -> CaptureResult:
    return CaptureResult(
        dialogue_id=str(payload.get("dialogue_id", "")),
        accepted_message_count=int(
            payload.get(
                "accepted_message_count",
                payload.get("accepted_event_count", 0),
            )
        ),
        unit_count=int(payload.get("unit_count", 0)),
        units=tuple(memory_unit_from_json(item) for item in _list(payload.get("units"))),
        skipped=tuple(capture_skip_from_json(item) for item in _list(payload.get("skipped"))),
        stats=_mapping(payload.get("stats")),
        trace_ref=_optional_str(payload.get("trace_ref")),
    )


def read_result_from_json(payload: dict[str, Any]) -> ReadResult:
    return ReadResult(
        request=read_request_from_json(_mapping(payload.get("request"))),
        ranked_units=tuple(
            ranked_memory_unit_from_json(item)
            for item in _list(payload.get("ranked_units"))
        ),
        context=packed_context_from_json(_mapping(payload.get("context"))),
        stats=_mapping(payload.get("stats")),
        trace_ref=_optional_str(payload.get("trace_ref")),
    )


def memory_scope_from_json(value: Any) -> MemoryScope:
    payload = _mapping(value)
    return MemoryScope(
        owner_id=str(payload.get("owner_id") or payload.get("user_id") or ""),
        namespace=_optional_str(payload.get("namespace")),
    )


def capture_dialogue_from_json(payload: dict[str, Any]) -> CaptureDialogue:
    dialogue = _mapping(payload.get("dialogue"))
    if dialogue:
        return CaptureDialogue(
            messages=tuple(
                dialogue_message_from_json(item)
                for item in _list(dialogue.get("messages"))
            ),
            occurred_at=str(dialogue.get("occurred_at", "")),
            metadata=_mapping(dialogue.get("metadata")),
        )
    legacy_events = _list(payload.get("events"))
    return CaptureDialogue(
        messages=tuple(_legacy_event_to_message(item) for item in legacy_events),
        occurred_at=str(
            payload.get("capture_time")
            or (legacy_events[0].get("timestamp") if legacy_events and isinstance(legacy_events[0], dict) else "")
            or ""
        ),
        metadata=_mapping(payload.get("metadata")),
    )


def dialogue_message_from_json(value: Any) -> DialogueMessage:
    payload = _mapping(value)
    return DialogueMessage(
        role=str(payload.get("role", "")),
        content=str(payload.get("content", "")),
        timestamp=str(payload.get("timestamp", "")),
        speaker_id=_optional_str(payload.get("speaker_id") or payload.get("speaker")),
        metadata=_mapping(payload.get("metadata")),
    )


def time_range_from_json(value: Any) -> TimeRange | None:
    if value is None:
        return None
    payload = _mapping(value)
    return TimeRange(
        start=_optional_str(payload.get("start")),
        end=_optional_str(payload.get("end")),
    )


def capture_skip_from_json(value: Any) -> CaptureSkip:
    payload = _mapping(value)
    return CaptureSkip(
        message_range=_message_range(payload.get("message_range")),
        reason=str(payload.get("reason", "")),
        detail=_optional_str(payload.get("detail")),
    )


def memory_unit_from_json(value: Any) -> MemoryUnit:
    payload = _mapping(value)
    confidence = payload.get("confidence", payload.get("extraction_confidence"))
    return MemoryUnit(
        unit_id=str(payload.get("unit_id", "")),
        scope=memory_scope_from_json(payload.get("scope")),
        text=str(payload.get("text", "")),
        memory_type=str(payload.get("memory_type", "uncertain")),
        timestamp=str(payload.get("timestamp", "")),
        available_at=str(payload.get("available_at", "")),
        dialogue_refs=tuple(
            dialogue_ref_from_json(item)
            for item in _list(payload.get("dialogue_refs"))
        ),
        confidence=_optional_float(confidence),
        retention_until=_optional_str(payload.get("retention_until")),
        redacted_at=_optional_str(payload.get("redacted_at")),
        metadata=_mapping(payload.get("metadata")),
    )


def dialogue_ref_from_json(value: Any) -> DialogueRef:
    payload = _mapping(value)
    return DialogueRef(
        dialogue_id=str(payload.get("dialogue_id", "")),
        message_range=_message_range(payload.get("message_range")),
    )


def ranked_memory_unit_from_json(value: Any) -> RankedMemoryUnit:
    payload = _mapping(value)
    return RankedMemoryUnit(
        unit=memory_unit_from_json(payload.get("unit")),
        rank=int(payload.get("rank", 0)),
        score=float(payload.get("score", 0.0)),
        retrieval_text=str(payload.get("retrieval_text", "")),
        score_breakdown=_mapping(payload.get("score_breakdown")),
    )


def packed_context_from_json(value: Any) -> PackedContext:
    payload = _mapping(value)
    return PackedContext(
        text=str(payload.get("text", "")),
        token_count=int(payload.get("token_count", 0)),
        unit_count=int(payload.get("unit_count", 0)),
    )


def _legacy_event_to_message(value: Any) -> DialogueMessage:
    payload = _mapping(value)
    metadata = {
        **_mapping(payload.get("metadata")),
        "event_id": payload.get("event_id"),
        "event_type": payload.get("event_type"),
    }
    if payload.get("event_type") in {"correction", "preference"}:
        metadata["memory_type"] = payload.get("event_type")
    return DialogueMessage(
        role=str(payload.get("role", "")),
        content=str(payload.get("content", "")),
        timestamp=str(payload.get("timestamp", "")),
        speaker_id=_optional_str(payload.get("speaker")),
        metadata=metadata,
    )


def _message_range(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("message_range must be a two item list")
    return (int(value[0]), int(value[1]))


def _query(value: Any) -> str | dict[str, Any]:
    if isinstance(value, dict):
        return value
    return str(value)


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected object, got {type(value).__name__}")
    return value


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Expected list, got {type(value).__name__}")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_recency_policy(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text not in {"recent", "balanced", "historical"}:
        raise ValueError(f"Unsupported recency_policy: {text}")
    return text


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
