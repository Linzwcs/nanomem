from __future__ import annotations

from dataclasses import asdict, replace

from nanomem.core.contracts import (
    CaptureRequest,
    CaptureResult,
    CaptureSkip,
    DialogueMessage,
    Dialogue,
    DialogueWindow,
    DialogueWindowSelector,
    ExtractionRequest,
    FlushRequest,
    FlushResult,
    MemoryScope,
    MemoryUnit,
    OperationLogEntry,
    Session,
)
from nanomem.core.errors import ConfigError, ContractError, ExtractionError
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.events import is_extractable_message
from nanomem.core.ids import new_id, stable_id
from nanomem.index.base import MemoryUnitIndex
from nanomem.store.base import MemoryStore
from nanomem.core.time import now_utc_iso


DEFAULT_NAMESPACE = "personal"
DEFAULT_MAX_DIALOGUE_TOKENS = 512


class CapturePipeline:
    def __init__(
        self,
        *,
        store: MemoryStore,
        index: MemoryUnitIndex,
        extractor: MemoryUnitExtractor,
        max_dialogue_tokens: int = DEFAULT_MAX_DIALOGUE_TOKENS,
    ) -> None:
        if max_dialogue_tokens <= 0:
            raise ConfigError("max_dialogue_tokens must be positive")
        self.store = store
        self.index = index
        self.extractor = extractor
        self.max_dialogue_tokens = max_dialogue_tokens

    def run(self, request: CaptureRequest) -> CaptureResult:
        _validate_capture_request(request)
        scope = _resolve_scope(request.scope)
        session_id = _resolve_session_id(request)
        dialogue, window = self._append_to_dialogue(
            request,
            session_id=session_id,
        )

        if window is None:
            result = self._extract_dialogue(
                dialogue,
                scope=scope,
                session_id=None,
                extraction_time=request.capture_time,
            )
        elif window.token_count >= self.max_dialogue_tokens:
            result = self._extract_dialogue(
                dialogue,
                scope=scope,
                session_id=window.session_id,
                extraction_time=request.capture_time,
                window=_seal_window(
                    window,
                    at=request.capture_time,
                    reason="token_limit",
                    dialogue=dialogue,
                ),
            )
        else:
            self.store.put_dialogue(dialogue)
            self.store.put_dialogue_window(window)
            result = CaptureResult(
                dialogue_id=dialogue.dialogue_id,
                accepted_message_count=len(request.dialogue.messages),
                unit_count=0,
                units=(),
                stats={
                    "capture_mode": "dialogue_window",
                    "dialogue_status": window.status,
                    "extraction_deferred": True,
                    "session_id": session_id,
                    "dialogue_token_count": window.token_count,
                    "max_dialogue_tokens": self.max_dialogue_tokens,
                },
            )

        self._record_capture_log(scope, dialogue, result, session_id=session_id)
        return result

    def flush(self, request: FlushRequest) -> FlushResult:
        flush_time = request.flush_time or now_utc_iso()
        windows = self.store.query_dialogue_windows(_flush_selector(request))
        if windows and request.session_id is None:
            raise ContractError("FlushRequest.session_id is required")
        if windows and request.scope is None:
            raise ContractError("FlushRequest.scope is required for extraction routing")
        scope = _resolve_scope(request.scope) if request.scope else None
        units: list[MemoryUnit] = []
        skipped: list[CaptureSkip] = []
        flushed_dialogue_ids: list[str] = []
        for window in windows:
            dialogue = self.store.get_dialogue(window.dialogue_id)
            if dialogue is None:
                continue
            result = self._extract_dialogue(
                dialogue,
                scope=scope,
                session_id=window.session_id,
                extraction_time=flush_time,
                window=_seal_window(
                    window,
                    at=flush_time,
                    reason="explicit_flush",
                    dialogue=dialogue,
                ),
            )
            units.extend(result.units)
            skipped.extend(result.skipped)
            flushed_dialogue_ids.append(window.dialogue_id)

        self.store.append_operation_log(
            OperationLogEntry(
                log_id=new_id("oplog"),
                operation_type="flush",
                created_at=flush_time,
                scope=scope,
                status="ok",
                summary={
                    "dialogue_count": len(flushed_dialogue_ids),
                    "unit_count": len(units),
                    "skipped_count": len(skipped),
                },
                payload={
                    "dialogue_ids": flushed_dialogue_ids,
                    "unit_ids": [unit.unit_id for unit in units],
                    "skipped": [_skip_payload(item) for item in skipped],
                    "session_id": request.session_id,
                },
            )
        )
        return FlushResult(
            dialogue_count=len(flushed_dialogue_ids),
            unit_count=len(units),
            units=tuple(units),
            skipped=tuple(skipped),
            stats={
                "capture_mode": "dialogue_window",
                "flushed_dialogue_ids": flushed_dialogue_ids,
            },
        )

    def _append_to_dialogue(
        self,
        request: CaptureRequest,
        *,
        session_id: str | None,
    ) -> tuple[Dialogue, DialogueWindow | None]:
        if session_id is None:
            messages = request.dialogue.messages
            return _new_dialogue(request, session_id=None, messages=messages), None

        self.store.put_session(
            Session(
                session_id=session_id,
                created_at=request.capture_time,
                updated_at=request.capture_time,
                metadata=_session_metadata(request),
            )
        )
        current_window = self._open_window(session_id=session_id)
        if current_window is None:
            messages = request.dialogue.messages
            dialogue = _new_dialogue(request, session_id=session_id, messages=messages)
            window = DialogueWindow(
                session_id=session_id,
                dialogue_id=dialogue.dialogue_id,
                status="open",
                token_count=_estimate_tokens(messages),
                message_count=len(messages),
                created_at=request.capture_time,
                updated_at=request.capture_time,
                metadata={"source": "capture_session"},
            )
            return dialogue, window

        current = self.store.get_dialogue(current_window.dialogue_id)
        if current is None:
            messages = request.dialogue.messages
            dialogue = _new_dialogue(request, session_id=session_id, messages=messages)
            window = replace(
                current_window,
                dialogue_id=dialogue.dialogue_id,
                updated_at=request.capture_time,
                token_count=_estimate_tokens(messages),
                message_count=len(messages),
            )
            return dialogue, window

        messages = current.messages + request.dialogue.messages
        dialogue = replace(
            current,
            messages=messages,
            ended_at=_last_timestamp(messages, request.dialogue.occurred_at),
            updated_at=request.capture_time,
            checksum=_dialogue_checksum(messages),
            metadata={
                **current.metadata,
                **dict(request.dialogue.metadata),
            },
        )
        window = replace(
            current_window,
            status="open",
            updated_at=request.capture_time,
            token_count=_estimate_tokens(messages),
            message_count=len(messages),
        )
        return dialogue, window

    def _open_window(
        self,
        *,
        session_id: str,
    ) -> DialogueWindow | None:
        rows = self.store.query_dialogue_windows(
            DialogueWindowSelector(
                session_id=session_id,
                statuses=("open",),
                limit=1,
            )
        )
        return rows[0] if rows else None

    def _extract_dialogue(
        self,
        dialogue: Dialogue,
        *,
        scope: MemoryScope,
        session_id: str | None,
        extraction_time: str,
        window: DialogueWindow | None = None,
    ) -> CaptureResult:
        self.store.put_dialogue(dialogue)
        if window is not None:
            self.store.put_dialogue_window(
                replace(
                    window,
                    status="extracting",
                    updated_at=extraction_time,
                    token_count=_estimate_tokens(dialogue.messages),
                    message_count=len(dialogue.messages),
                )
            )
        extraction = self.extractor.extract(
            ExtractionRequest(
                scope=scope,
                dialogue=dialogue,
                extraction_time=extraction_time,
            )
        )
        _validate_extraction_units(
            extraction.units,
            scope=scope,
            dialogue=dialogue,
        )
        self.store.append_units(extraction.units)
        self.index.upsert(extraction.units)
        if window is not None:
            self.store.put_dialogue_window(
                replace(
                    window,
                    status="extracted",
                    updated_at=extraction_time,
                    extracted_at=extraction_time,
                    token_count=_estimate_tokens(dialogue.messages),
                    message_count=len(dialogue.messages),
                )
            )
        return CaptureResult(
            dialogue_id=dialogue.dialogue_id,
            accepted_message_count=len(dialogue.messages),
            unit_count=len(extraction.units),
            units=extraction.units,
            skipped=extraction.skipped,
            stats={
                "capture_mode": "dialogue_window",
                "dialogue_status": "extracted",
                "extraction_deferred": False,
                "extractor": self.extractor.name,
                "inserted_unit_count": len(extraction.units),
                "session_id": session_id,
                "dialogue_token_count": _estimate_tokens(dialogue.messages),
                "max_dialogue_tokens": self.max_dialogue_tokens,
                **extraction.stats,
            },
        )

    def _record_capture_log(
        self,
        scope: MemoryScope,
        dialogue: Dialogue,
        result: CaptureResult,
        *,
        session_id: str | None,
    ) -> None:
        created_at = now_utc_iso()
        self.store.append_operation_log(
            OperationLogEntry(
                log_id=new_id("oplog"),
                operation_type="capture",
                created_at=created_at,
                scope=scope,
                status="ok",
                summary={
                    "dialogue_id": dialogue.dialogue_id,
                    "session_id": session_id,
                    "message_count": len(dialogue.messages),
                    "unit_count": result.unit_count,
                    "skipped_count": len(result.skipped),
                    "dialogue_status": result.stats.get("dialogue_status"),
                },
                payload={
                    "unit_ids": [unit.unit_id for unit in result.units],
                    "skipped": [_skip_payload(item) for item in result.skipped],
                    "stats": result.stats,
                },
            )
        )


def _validate_capture_request(request: CaptureRequest) -> None:
    if not request.scope.owner_id:
        raise ContractError("CaptureRequest.scope.owner_id is required")
    if not request.capture_time:
        raise ContractError("CaptureRequest.capture_time is required")
    if not request.dialogue.occurred_at:
        raise ContractError("CaptureRequest.dialogue.occurred_at is required")
    if not request.dialogue.messages:
        raise ContractError("CaptureRequest.dialogue.messages is required")
    for index, message in enumerate(request.dialogue.messages):
        if not message.timestamp:
            raise ContractError(f"DialogueMessage[{index}].timestamp is required")


def _resolve_scope(scope: MemoryScope) -> MemoryScope:
    if scope.namespace:
        return scope
    return replace(scope, namespace=DEFAULT_NAMESPACE)


def _resolve_session_id(request: CaptureRequest) -> str | None:
    if request.session_id:
        return request.session_id
    metadata_session = request.dialogue.metadata.get("session_id")
    if metadata_session:
        return str(metadata_session)
    return None


def _flush_selector(request: FlushRequest) -> DialogueWindowSelector:
    return DialogueWindowSelector(
        session_id=request.session_id,
        statuses=("open", "sealed"),
        order="oldest_first",
        limit=None,
    )


def _new_dialogue(
    request: CaptureRequest,
    *,
    session_id: str | None,
    messages: tuple[DialogueMessage, ...],
) -> Dialogue:
    return Dialogue(
        dialogue_id=new_id("dlg"),
        session_id=session_id,
        messages=messages,
        started_at=_first_timestamp(messages, request.dialogue.occurred_at),
        ended_at=_last_timestamp(messages, request.dialogue.occurred_at),
        created_at=request.capture_time,
        updated_at=request.capture_time,
        checksum=_dialogue_checksum(messages),
        metadata=dict(request.dialogue.metadata),
    )


def _session_metadata(request: CaptureRequest) -> dict[str, object]:
    return {
        key: value
        for key, value in request.dialogue.metadata.items()
        if key not in {"session_id"}
    }


def _seal_window(
    window: DialogueWindow,
    *,
    at: str,
    reason: str,
    dialogue: Dialogue,
) -> DialogueWindow:
    return replace(
        window,
        status="sealed",
        updated_at=at,
        sealed_at=at,
        seal_reason=reason,
        token_count=_estimate_tokens(dialogue.messages),
        message_count=len(dialogue.messages),
    )


def _dialogue_checksum(messages: tuple[object, ...]) -> str:
    return stable_id(
        "dlgchk",
        {"messages": [asdict(message) for message in messages]},
    )


def _estimate_tokens(messages: tuple[object, ...]) -> int:
    count = 0
    for message in messages:
        content = getattr(message, "content", "")
        count += max(1, (len(str(content)) + 3) // 4)
    return count


def _first_timestamp(messages: tuple[object, ...], fallback: str) -> str:
    if not messages:
        return fallback
    return str(getattr(messages[0], "timestamp", "") or fallback)


def _last_timestamp(messages: tuple[object, ...], fallback: str) -> str:
    if not messages:
        return fallback
    return str(getattr(messages[-1], "timestamp", "") or fallback)


def _validate_extraction_units(
    units: tuple[MemoryUnit, ...],
    *,
    scope: MemoryScope,
    dialogue: Dialogue,
) -> None:
    for unit in units:
        if unit.scope != scope:
            raise ExtractionError(f"MemoryUnit {unit.unit_id} has unexpected scope")
        if not unit.text.strip():
            raise ExtractionError(f"MemoryUnit {unit.unit_id} text is required")
        if not unit.memory_type:
            raise ExtractionError(f"MemoryUnit {unit.unit_id} memory_type is required")
        if not unit.timestamp:
            raise ExtractionError(f"MemoryUnit {unit.unit_id} timestamp is required")
        if not unit.available_at:
            raise ExtractionError(f"MemoryUnit {unit.unit_id} available_at is required")
        for ref in unit.dialogue_refs:
            if ref.dialogue_id != dialogue.dialogue_id:
                raise ExtractionError(
                    f"MemoryUnit {unit.unit_id} references a different dialogue"
                )
            if ref.message_range is None:
                continue
            start, end = ref.message_range
            if start < 0 or end <= start or end > len(dialogue.messages):
                raise ExtractionError(
                    f"MemoryUnit {unit.unit_id} has invalid dialogue ref range"
                )
            if not all(
                is_extractable_message(message)
                for message in dialogue.messages[start:end]
            ):
                raise ExtractionError(
                    f"MemoryUnit {unit.unit_id} references non-extractable evidence"
                )


def _skip_payload(skip: CaptureSkip) -> dict[str, object]:
    return {
        "message_range": skip.message_range,
        "reason": skip.reason,
        "detail": skip.detail,
    }
