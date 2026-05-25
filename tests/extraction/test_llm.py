from __future__ import annotations

import json
from typing import Any

from nanomem.contracts import (
    CaptureSkip,
    DialogueMessage,
    Dialogue,
    ExtractionRequest,
    ExtractionResult,
    MemoryScope,
    MemoryUnit,
)
from nanomem.extraction.llm import LLMMemoryUnitExtractor


class FakeCompletionClient:
    def __init__(
        self,
        payload: dict[str, Any] | Exception | list[dict[str, Any] | Exception],
    ) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
    ) -> dict[str, Any]:
        call_index = len(self.calls)
        self.calls.append({"model": model, "messages": messages})
        payload = (
            self.payload[call_index]
            if isinstance(self.payload, list)
            else self.payload
        )
        if isinstance(payload, Exception):
            raise payload
        return payload


class FakeFallbackExtractor:
    name = "fake_fallback"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(
            units=(
                MemoryUnit(
                    unit_id="fallback-unit",
                    scope=request.scope,
                    text="The user prefers concise answers.",
                    memory_type="preference",
                    timestamp=request.dialogue.messages[0].timestamp,
                    available_at=request.extraction_time or request.dialogue.updated_at,
                ),
            ),
            skipped=(),
            stats={"extractor": self.name},
        )


def test_llm_extractor_parses_units_with_dialogue_ref_and_metadata() -> None:
    client = FakeCompletionClient(
        {
            "units": [
                {
                    "text": "The user said they prefer concise Chinese answers.",
                    "message_range": [1, 2],
                    "memory_type": "preference",
                    "evidence_role": "user",
                    "source_speaker_id": "user-1",
                }
            ],
            "skipped": [],
        }
    )
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=client,
    )

    result = extractor.extract(_request())

    assert len(result.units) == 1
    unit = result.units[0]
    assert unit.text == "The user said they prefer concise Chinese answers."
    assert unit.memory_type == "preference"
    assert unit.timestamp == "2026-01-01T00:00:10+00:00"
    assert unit.available_at == "2026-01-01T00:00:30+00:00"
    assert unit.dialogue_refs[0].dialogue_id == "dlg-1"
    assert unit.dialogue_refs[0].message_range == (1, 2)
    assert unit.metadata["extractor"] == "llm_v1"
    assert unit.metadata["model"] == "test-model"
    assert unit.metadata["evidence_role"] == "user"
    assert unit.metadata["source_speaker_id"] == "user-1"


def test_llm_extractor_defaults_missing_message_range_to_whole_dialogue() -> None:
    client = FakeCompletionClient(
        {
            "units": [
                {
                    "text": "The user said they prefer concise Chinese answers.",
                    "memory_type": "preference",
                }
            ],
            "skipped": [],
        }
    )
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=client,
    )

    result = extractor.extract(_request())

    unit = result.units[0]
    assert unit.dialogue_refs[0].dialogue_id == "dlg-1"
    assert unit.dialogue_refs[0].message_range is None
    assert unit.timestamp == "2026-01-01T00:00:30+00:00"


def test_llm_extractor_sends_only_extractable_visible_messages() -> None:
    client = FakeCompletionClient({"units": [], "skipped": []})
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=client,
    )
    request = _request(
        messages=(
            _message("user", "I prefer concise answers.", 0),
            _message("tool", "raw tool output", 1),
            _message("user", "hidden note", 2, metadata={"hidden": True}),
        )
    )

    result = extractor.extract(request)

    sent = json.loads(client.calls[0]["messages"][1]["content"])["messages"]
    assert [item["index"] for item in sent] == [0]
    assert [item.reason for item in result.skipped] == [
        "invalid_role",
        "hidden_or_tool_message",
    ]


def test_llm_extractor_invalid_payload_uses_fallback() -> None:
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=FakeCompletionClient(
            {
                "units": [
                    {
                        "text": "The user prefers concise answers.",
                        "message_range": [99, 100],
                        "memory_type": "preference",
                    }
                ],
                "skipped": [],
            }
        ),
        fallback=FakeFallbackExtractor(),
    )

    result = extractor.extract(_request())

    assert result.units[0].unit_id == "fallback-unit"
    assert result.stats["llm_fallback"] is True
    assert result.stats["llm_fallback_reason"] == "invalid_payload"


def test_llm_extractor_rejects_ranges_that_cross_hidden_messages() -> None:
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=FakeCompletionClient(
            {
                "units": [
                    {
                        "text": "The user prefers concise answers.",
                        "message_range": [0, 3],
                        "memory_type": "preference",
                    }
                ],
                "skipped": [],
            }
        ),
        fallback=FakeFallbackExtractor(),
    )
    request = _request(
        messages=(
            _message("user", "I prefer concise answers.", 0),
            _message("tool", "raw tool output", 1),
            _message("user", "Please keep answers short.", 2),
        )
    )

    result = extractor.extract(request)

    assert result.units[0].unit_id == "fallback-unit"
    assert result.stats["llm_fallback_reason"] == "invalid_payload"


def test_llm_extractor_missing_api_key_uses_fallback() -> None:
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        fallback=FakeFallbackExtractor(),
    )

    result = extractor.extract(_request())

    assert result.units[0].unit_id == "fallback-unit"
    assert result.stats["llm_fallback_reason"] == "missing_api_key"


def test_llm_extractor_completion_error_uses_fallback() -> None:
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=FakeCompletionClient(RuntimeError("network unavailable")),
        fallback=FakeFallbackExtractor(),
    )

    result = extractor.extract(_request())

    assert result.units[0].unit_id == "fallback-unit"
    assert result.stats["llm_fallback_reason"] == "llm_error"


def test_llm_extractor_chunks_role_aware_exchanges() -> None:
    client = FakeCompletionClient(
        [
            {
                "units": [
                    {
                        "text": "The user prefers concise answers.",
                        "message_range": [0, 1],
                        "memory_type": "preference",
                    }
                ],
                "skipped": [],
            },
            {
                "units": [
                    {
                        "text": "The user wants source citations.",
                        "message_range": [2, 3],
                        "memory_type": "preference",
                    }
                ],
                "skipped": [],
            },
        ]
    )
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=client,
        max_messages_per_chunk=2,
    )

    result = extractor.extract(
        _request(
            messages=(
                _message("user", "I prefer concise answers.", 0),
                _message("assistant", "I will keep answers short.", 1),
                _message("user", "Please include source citations.", 2),
                _message("assistant", "I will cite sources when needed.", 3),
            )
        )
    )

    sent_chunks = [
        json.loads(call["messages"][1]["content"])["messages"]
        for call in client.calls
    ]
    assert [[item["index"] for item in chunk] for chunk in sent_chunks] == [
        [0, 1],
        [2, 3],
    ]
    assert [unit.dialogue_refs[0].message_range for unit in result.units] == [
        (0, 1),
        (2, 3),
    ]
    assert result.stats["chunk_count"] == 2
    assert result.units[0].metadata["chunk_id"] == 0
    assert result.units[1].metadata["chunk_id"] == 1


def test_llm_extractor_splits_chunks_at_non_extractable_gaps() -> None:
    client = FakeCompletionClient(
        [
            {"units": [], "skipped": []},
            {"units": [], "skipped": []},
        ]
    )
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=client,
    )

    result = extractor.extract(
        _request(
            messages=(
                _message("user", "I prefer concise answers.", 0),
                _message("tool", "raw output", 1),
                _message("user", "I want source citations.", 2),
            )
        )
    )

    sent_chunks = [
        json.loads(call["messages"][1]["content"])["messages"]
        for call in client.calls
    ]
    assert [[item["index"] for item in chunk] for chunk in sent_chunks] == [
        [0],
        [2],
    ]
    assert result.stats["chunk_count"] == 2
    assert [skip.reason for skip in result.skipped] == ["invalid_role"]


def test_llm_extractor_rejects_ranges_outside_current_chunk() -> None:
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=FakeCompletionClient(
            [
                {
                    "units": [
                        {
                            "text": "The user wants source citations.",
                            "message_range": [2, 3],
                            "memory_type": "preference",
                        }
                    ],
                    "skipped": [],
                }
            ]
        ),
        fallback=FakeFallbackExtractor(),
        max_messages_per_chunk=2,
    )

    result = extractor.extract(
        _request(
            messages=(
                _message("user", "I prefer concise answers.", 0),
                _message("assistant", "I will keep answers short.", 1),
                _message("user", "Please include source citations.", 2),
            )
        )
    )

    assert result.units[0].unit_id == "fallback-unit"
    assert result.stats["llm_fallback_reason"] == "invalid_payload"


def _request(
    messages: tuple[DialogueMessage, ...] | None = None,
) -> ExtractionRequest:
    return ExtractionRequest(
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        dialogue=Dialogue(
            dialogue_id="dlg-1",
            session_id=None,
            messages=messages
            or (
                _message("assistant", "What should I remember?", 0),
                _message("user", "I prefer concise Chinese answers.", 1),
            ),
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:00:30+00:00",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:30+00:00",
        ),
        extraction_time="2026-01-01T00:00:30+00:00",
    )


def _message(
    role: str,
    content: str,
    offset: int,
    *,
    metadata: dict[str, Any] | None = None,
) -> DialogueMessage:
    return DialogueMessage(
        role=role,
        content=content,
        timestamp=f"2026-01-01T00:00:{offset * 10:02d}+00:00",
        speaker_id="user-1" if role == "user" else role,
        metadata=dict(metadata or {}),
    )
