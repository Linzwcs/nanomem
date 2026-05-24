from __future__ import annotations

from dataclasses import asdict, replace

from nanomem.contracts import (
    CaptureRequest,
    CaptureResult,
    CaptureSkip,
    DialogueRecord,
    DialogueSelector,
    ExtractionRequest,
    FlushRequest,
    FlushResult,
    MemoryScope,
    MemoryUnit,
    OperationLogEntry,
)
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.events import is_extractable_message
from nanomem.ids import new_id, stable_id
from nanomem.index.base import MemoryUnitIndex
from nanomem.store.base import MemoryStore
from nanomem.time import now_utc_iso


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
            raise ValueError("max_dialogue_tokens must be positive")
        self.store = store
        self.index = index
        self.extractor = extractor
        self.max_dialogue_tokens = max_dialogue_tokens

    def run(self, request: CaptureRequest) -> CaptureResult:
        _validate_capture_request(request)
        scope = _resolve_scope(request.scope)
        session_id = _resolve_session_id(request)
        dialogue = self._append_to_dialogue(request, scope=scope, session_id=session_id)

        if session_id is None or dialogue.token_count >= self.max_dialogue_tokens:
            result = self._extract_dialogue(
                replace(dialogue, status="sealed"),
                extraction_time=request.capture_time,
            )
        else:
            self.store.put_dialogue(dialogue)
            result = CaptureResult(
                dialogue_id=dialogue.dialogue_id,
                accepted_message_count=len(request.dialogue.messages),
                unit_count=0,
                units=(),
                stats={
                    "capture_mode": "dialogue_window",
                    "dialogue_status": dialogue.status,
                    "extraction_deferred": True,
                    "session_id": session_id,
                    "dialogue_token_count": dialogue.token_count,
                    "max_dialogue_tokens": self.max_dialogue_tokens,
                },
            )

        self._record_capture_log(scope, dialogue, result)
        return result

    def flush(self, request: FlushRequest) -> FlushResult:
        flush_time = request.flush_time or now_utc_iso()
        selector = _flush_selector(request)
        dialogues = self.store.query_dialogues(selector)
        units: list[MemoryUnit] = []
        skipped: list[CaptureSkip] = []
        for dialogue in dialogues:
            result = self._extract_dialogue(
                replace(dialogue, status="sealed"),
                extraction_time=flush_time,
            )
            units.extend(result.units)
            skipped.extend(result.skipped)

        scope = _resolve_scope(request.scope) if request.scope else None
        self.store.append_operation_log(
            OperationLogEntry(
                log_id=new_id("oplog"),
                operation_type="flush",
                created_at=flush_time,
                scope=scope,
                status="ok",
                summary={
                    "dialogue_count": len(dialogues),
                    "unit_count": len(units),
                    "skipped_count": len(skipped),
                },
                payload={
                    "dialogue_ids": [dialogue.dialogue_id for dialogue in dialogues],
                    "unit_ids": [unit.unit_id for unit in units],
                    "skipped": [_skip_payload(item) for item in skipped],
                    "session_id": request.session_id,
                },
            )
        )
        return FlushResult(
            dialogue_count=len(dialogues),
            unit_count=len(units),
            units=tuple(units),
            skipped=tuple(skipped),
            stats={
                "capture_mode": "dialogue_window",
                "flushed_dialogue_ids": [dialogue.dialogue_id for dialogue in dialogues],
            },
        )

    def _append_to_dialogue(
        self,
        request: CaptureRequest,
        *,
        scope: MemoryScope,
        session_id: str | None,
    ) -> DialogueRecord:
        current = (
            self._open_dialogue(scope=scope, session_id=session_id)
            if session_id is not None
            else None
        )
        if current is None:
            messages = request.dialogue.messages
            return DialogueRecord(
                dialogue_id=new_id("dlg"),
                scope=scope,
                session_id=session_id,
                messages=messages,
                status="open",
                started_at=_first_timestamp(messages, request.dialogue.occurred_at),
                ended_at=_last_timestamp(messages, request.dialogue.occurred_at),
                created_at=request.capture_time,
                updated_at=request.capture_time,
                token_count=_estimate_tokens(messages),
                checksum=_dialogue_checksum(scope, session_id, messages),
                metadata=dict(request.dialogue.metadata),
            )

        messages = current.messages + request.dialogue.messages
        return replace(
            current,
            messages=messages,
            status="open",
            ended_at=_last_timestamp(messages, request.dialogue.occurred_at),
            updated_at=request.capture_time,
            token_count=_estimate_tokens(messages),
            checksum=_dialogue_checksum(scope, session_id, messages),
            metadata={
                **current.metadata,
                **dict(request.dialogue.metadata),
            },
        )

    def _open_dialogue(
        self,
        *,
        scope: MemoryScope,
        session_id: str,
    ) -> DialogueRecord | None:
        rows = self.store.query_dialogues(
            DialogueSelector(
                owner_id=scope.owner_id,
                namespaces=(str(scope.namespace),),
                session_id=session_id,
                statuses=("open",),
                limit=1,
            )
        )
        return rows[0] if rows else None

    def _extract_dialogue(
        self,
        dialogue: DialogueRecord,
        *,
        extraction_time: str,
    ) -> CaptureResult:
        sealed = replace(
            dialogue,
            status="sealed",
            updated_at=extraction_time,
            token_count=_estimate_tokens(dialogue.messages),
            checksum=_dialogue_checksum(
                dialogue.scope,
                dialogue.session_id,
                dialogue.messages,
            ),
        )
        self.store.put_dialogue(sealed)
        extraction = self.extractor.extract(
            ExtractionRequest(
                scope=dialogue.scope,
                dialogue=sealed,
                extraction_time=extraction_time,
            )
        )
        _validate_extraction_units(
            extraction.units,
            scope=dialogue.scope,
            dialogue=sealed,
        )
        self.store.append_units(extraction.units)
        self.index.upsert(extraction.units)
        extracted = replace(
            sealed,
            status="extracted",
            updated_at=extraction_time,
            extracted_at=extraction_time,
        )
        self.store.put_dialogue(extracted)
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
                "session_id": dialogue.session_id,
                "dialogue_token_count": extracted.token_count,
                "max_dialogue_tokens": self.max_dialogue_tokens,
                **extraction.stats,
            },
        )

    def _record_capture_log(
        self,
        scope: MemoryScope,
        dialogue: DialogueRecord,
        result: CaptureResult,
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
                    "session_id": dialogue.session_id,
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
        raise ValueError("CaptureRequest.scope.owner_id is required")
    if not request.capture_time:
        raise ValueError("CaptureRequest.capture_time is required")
    if not request.dialogue.occurred_at:
        raise ValueError("CaptureRequest.dialogue.occurred_at is required")
    if not request.dialogue.messages:
        raise ValueError("CaptureRequest.dialogue.messages is required")
    for index, message in enumerate(request.dialogue.messages):
        if not message.timestamp:
            raise ValueError(f"DialogueMessage[{index}].timestamp is required")


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


def _flush_selector(request: FlushRequest) -> DialogueSelector:
    scope = _resolve_scope(request.scope) if request.scope else None
    return DialogueSelector(
        owner_id=scope.owner_id if scope else None,
        namespaces=(scope.namespace,) if scope and scope.namespace else None,
        session_id=request.session_id,
        statuses=("open", "sealed"),
        order="oldest_first",
        limit=None,
    )


def _dialogue_checksum(
    scope: MemoryScope,
    session_id: str | None,
    messages: tuple[object, ...],
) -> str:
    return stable_id(
        "dlgchk",
        {
            "scope": asdict(scope),
            "session_id": session_id,
            "messages": [asdict(message) for message in messages],
        },
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
    dialogue: DialogueRecord,
) -> None:
    for unit in units:
        if unit.scope != scope:
            raise ValueError(f"MemoryUnit {unit.unit_id} has unexpected scope")
        if not unit.text.strip():
            raise ValueError(f"MemoryUnit {unit.unit_id} text is required")
        if not unit.memory_type:
            raise ValueError(f"MemoryUnit {unit.unit_id} memory_type is required")
        if not unit.timestamp:
            raise ValueError(f"MemoryUnit {unit.unit_id} timestamp is required")
        if not unit.available_at:
            raise ValueError(f"MemoryUnit {unit.unit_id} available_at is required")
        for ref in unit.dialogue_refs:
            if ref.dialogue_id != dialogue.dialogue_id:
                raise ValueError(
                    f"MemoryUnit {unit.unit_id} references a different dialogue"
                )
            if ref.message_range is None:
                continue
            start, end = ref.message_range
            if start < 0 or end <= start or end > len(dialogue.messages):
                raise ValueError(
                    f"MemoryUnit {unit.unit_id} has invalid dialogue ref range"
                )
            if not all(
                is_extractable_message(message)
                for message in dialogue.messages[start:end]
            ):
                raise ValueError(
                    f"MemoryUnit {unit.unit_id} references non-extractable evidence"
                )


def _skip_payload(skip: CaptureSkip) -> dict[str, object]:
    return {
        "message_range": skip.message_range,
        "reason": skip.reason,
        "detail": skip.detail,
    }
