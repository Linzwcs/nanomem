from __future__ import annotations

import pytest

from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueRef,
    DialogueMessage,
    ExtractionRequest,
    ExtractionResult,
    MemoryScope,
    MemoryUnit,
)
from nanomem.service.core import NanoMemService


class BadDialogueRefExtractor:
    name = "bad_ref"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(
            units=(
                MemoryUnit(
                    unit_id="unit-bad",
                    scope=request.scope,
                    text="The user prefers concise answers.",
                    memory_type="preference",
                    timestamp=request.dialogue.started_at,
                    available_at=request.extraction_time or request.dialogue.updated_at,
                    dialogue_refs=(
                        DialogueRef(
                            dialogue_id=request.dialogue.dialogue_id,
                            message_range=(4, 5),
                        ),
                    ),
                ),
            )
        )


class HiddenDialogueRefExtractor:
    name = "hidden_ref"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(
            units=(
                MemoryUnit(
                    unit_id="unit-hidden",
                    scope=request.scope,
                    text="The user prefers concise answers.",
                    memory_type="preference",
                    timestamp=request.dialogue.started_at,
                    available_at=request.extraction_time or request.dialogue.updated_at,
                    dialogue_refs=(
                        DialogueRef(
                            dialogue_id=request.dialogue.dialogue_id,
                            message_range=(0, 2),
                        ),
                    ),
                ),
            )
        )


def test_capture_rejects_extractor_units_with_invalid_dialogue_ref_range() -> None:
    service = NanoMemService(extractor=BadDialogueRefExtractor())

    with pytest.raises(ValueError, match="invalid dialogue ref range"):
        service.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                dialogue=CaptureDialogue(
                    messages=(
                        DialogueMessage(
                            role="user",
                            content="I prefer concise answers.",
                            timestamp="2026-01-01T00:00:00+00:00",
                        ),
                    ),
                    occurred_at="2026-01-01T00:00:00+00:00",
                ),
                capture_time="2026-01-01T00:00:01+00:00",
            )
        )


def test_capture_rejects_extractor_units_with_hidden_dialogue_ref_range() -> None:
    service = NanoMemService(extractor=HiddenDialogueRefExtractor())

    with pytest.raises(ValueError, match="non-extractable evidence"):
        service.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                dialogue=CaptureDialogue(
                    messages=(
                        DialogueMessage(
                            role="user",
                            content="I prefer concise answers.",
                            timestamp="2026-01-01T00:00:00+00:00",
                        ),
                        DialogueMessage(
                            role="tool",
                            content="raw tool output",
                            timestamp="2026-01-01T00:00:01+00:00",
                        ),
                    ),
                    occurred_at="2026-01-01T00:00:00+00:00",
                ),
                capture_time="2026-01-01T00:00:02+00:00",
            )
        )
