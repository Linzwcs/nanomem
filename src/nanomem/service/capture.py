from __future__ import annotations

from dataclasses import asdict, replace

from nanomem.contracts import (
    CaptureRequest,
    CaptureResult,
    CaptureSkip,
    DialogueRecord,
    ExtractionRequest,
    MemoryUnit,
    MemoryScope,
    OperationLogEntry,
)
from nanomem.extraction.base import MemoryUnitExtractor
from nanomem.extraction.events import is_extractable_message
from nanomem.ids import new_id, stable_id
from nanomem.index.base import MemoryUnitIndex
from nanomem.store.base import MemoryStore
from nanomem.time import now_utc_iso


DEFAULT_NAMESPACE = "personal"


class CapturePipeline:
    def __init__(
        self,
        *,
        store: MemoryStore,
        index: MemoryUnitIndex,
        extractor: MemoryUnitExtractor,
    ) -> None:
        self.store = store
        self.index = index
        self.extractor = extractor

    def run(self, request: CaptureRequest) -> CaptureResult:
        _validate_capture_request(request)
        scope = _resolve_scope(request.scope)
        dialogue = _dialogue_record(request, scope=scope)
        self.store.put_dialogue(dialogue)

        extraction = self.extractor.extract(
            ExtractionRequest(
                scope=scope,
                dialogue=dialogue,
            )
        )
        _validate_extraction_units(
            extraction.units,
            scope=scope,
            dialogue=dialogue,
        )
        self.store.append_units(extraction.units)
        self.index.upsert(extraction.units)

        result = CaptureResult(
            dialogue_id=dialogue.dialogue_id,
            accepted_message_count=len(dialogue.messages),
            unit_count=len(extraction.units),
            units=extraction.units,
            skipped=extraction.skipped,
            stats={
                "extractor": self.extractor.name,
                "inserted_unit_count": len(extraction.units),
                **extraction.stats,
            },
        )
        self._record_capture_log(scope, dialogue, result)
        return result

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
                    "message_count": len(dialogue.messages),
                    "unit_count": result.unit_count,
                    "skipped_count": len(result.skipped),
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


def _dialogue_record(
    request: CaptureRequest,
    *,
    scope: MemoryScope,
) -> DialogueRecord:
    checksum_payload = {
        "scope": asdict(scope),
        "occurred_at": request.dialogue.occurred_at,
        "messages": [asdict(message) for message in request.dialogue.messages],
    }
    checksum = stable_id("dlgchk", checksum_payload)
    return DialogueRecord(
        dialogue_id=stable_id("dlg", checksum_payload),
        messages=request.dialogue.messages,
        occurred_at=request.dialogue.occurred_at,
        captured_at=request.capture_time,
        checksum=checksum,
        metadata=dict(request.dialogue.metadata),
    )


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
        if unit.confidence is not None and not (0.0 <= unit.confidence <= 1.0):
            raise ValueError(f"MemoryUnit {unit.unit_id} confidence is out of range")
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
