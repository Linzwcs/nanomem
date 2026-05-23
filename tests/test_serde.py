from __future__ import annotations

import pytest

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
)
from nanomem.serde import (
    capture_request_from_json,
    capture_result_from_json,
    capture_request_to_json,
    capture_result_to_json,
    memory_unit_from_json,
    read_request_from_json,
    read_result_from_json,
    read_request_to_json,
    read_result_to_json,
)
from nanomem.service.core import NanoMemService


def test_capture_request_from_dialogue_json() -> None:
    request = capture_request_from_json(
        {
            "scope": {"owner_id": "user-1", "namespace": "personal"},
            "dialogue": {
                "occurred_at": "2026-01-05T00:00:00+00:00",
                "messages": [
                    {
                        "role": "user",
                        "speaker_id": "user-1",
                        "content": "I prefer concise Chinese answers.",
                        "timestamp": "2026-01-05T00:00:00+00:00",
                    }
                ],
                "metadata": {"channel": "chat"},
            },
            "capture_time": "2026-01-05T00:00:01+00:00",
        }
    )

    assert request.scope.owner_id == "user-1"
    assert request.scope.namespace == "personal"
    assert request.dialogue.messages[0].speaker_id == "user-1"
    assert request.dialogue.metadata == {"channel": "chat"}

    serialized = capture_request_to_json(request)
    assert serialized["scope"] == {"owner_id": "user-1", "namespace": "personal"}
    assert isinstance(serialized["dialogue"]["messages"], list)
    assert serialized["dialogue"]["messages"][0]["role"] == "user"
    assert serialized["dialogue"]["messages"][0]["metadata"] == {}


def test_read_request_uses_owner_namespace_and_optional_recency_policy() -> None:
    request = read_request_from_json(
        {
            "scope": {"user_id": "legacy-user", "namespace": "personal"},
            "query": "answer style",
            "query_time": "2026-01-06T00:00:00+00:00",
        }
    )

    assert request.owner_id == "legacy-user"
    assert request.namespaces == ("personal",)
    assert request.recency_policy is None

    serialized = read_request_to_json(request)
    assert serialized["owner_id"] == "legacy-user"
    assert serialized["namespaces"] == ["personal"]


def test_read_request_rejects_unknown_recency_policy() -> None:
    with pytest.raises(ValueError, match="Unsupported recency_policy"):
        read_request_from_json(
            {
                "owner_id": "user-1",
                "query": "answer style",
                "query_time": "2026-01-06T00:00:00+00:00",
                "recency_policy": "yesterday",
            }
        )


def test_capture_request_supports_legacy_event_payload() -> None:
    request = capture_request_from_json(
        {
            "scope": {"user_id": "legacy-user", "namespace": "personal"},
            "events": [
                {
                    "event_id": "evt-1",
                    "event_type": "preference",
                    "role": "user",
                    "speaker": "legacy-user",
                    "content": "I prefer concise answers.",
                    "timestamp": "2026-01-05T00:00:00+00:00",
                    "metadata": {"source": "legacy"},
                }
            ],
            "capture_time": "2026-01-05T00:00:01+00:00",
        }
    )

    assert request.scope.owner_id == "legacy-user"
    assert request.dialogue.occurred_at == "2026-01-05T00:00:01+00:00"
    message = request.dialogue.messages[0]
    assert message.speaker_id == "legacy-user"
    assert message.metadata["event_id"] == "evt-1"
    assert message.metadata["event_type"] == "preference"
    assert message.metadata["memory_type"] == "preference"


def test_read_request_namespaces_none_means_all_namespaces() -> None:
    request = read_request_from_json(
        {
            "owner_id": "user-1",
            "query": {"question": "answer style"},
            "query_time": "2026-01-06T00:00:00+00:00",
        }
    )

    assert request.namespaces is None
    assert request.query == {"question": "answer style"}


def test_read_request_explicit_namespace_list_is_preserved() -> None:
    request = read_request_from_json(
        {
            "owner_id": "user-1",
            "namespaces": ["personal", "work"],
            "query": "NanoMem design",
            "query_time": "2026-01-06T00:00:00+00:00",
        }
    )

    assert request.namespaces == ("personal", "work")


def test_memory_unit_from_json_parses_dialogue_ref_message_range() -> None:
    unit = memory_unit_from_json(
        {
            "unit_id": "unit-1",
            "scope": {"owner_id": "user-1", "namespace": "personal"},
            "text": "The user prefers concise answers.",
            "memory_type": "preference",
            "timestamp": "2026-01-05T00:00:00+00:00",
            "available_at": "2026-01-05T00:00:01+00:00",
            "dialogue_refs": [
                {"dialogue_id": "dlg-1", "message_range": [1, 3]},
            ],
            "metadata": {"extractor": "test"},
        }
    )

    assert unit.dialogue_refs[0].dialogue_id == "dlg-1"
    assert unit.dialogue_refs[0].message_range == (1, 3)
    assert unit.metadata == {"extractor": "test"}


def test_dialogue_ref_rejects_invalid_message_range_shape() -> None:
    with pytest.raises(ValueError, match="message_range must be a two item list"):
        memory_unit_from_json(
            {
                "unit_id": "unit-1",
                "scope": {"owner_id": "user-1", "namespace": "personal"},
                "text": "The user prefers concise answers.",
                "memory_type": "preference",
                "timestamp": "2026-01-05T00:00:00+00:00",
                "available_at": "2026-01-05T00:00:01+00:00",
                "dialogue_refs": [
                    {"dialogue_id": "dlg-1", "message_range": [1]},
                ],
            }
        )


def test_metadata_fields_must_be_json_objects() -> None:
    with pytest.raises(ValueError, match="Expected object"):
        capture_request_from_json(
            {
                "scope": {"owner_id": "user-1"},
                "dialogue": {
                    "occurred_at": "2026-01-05T00:00:00+00:00",
                    "messages": [
                        {
                            "role": "user",
                            "content": "I prefer concise answers.",
                            "timestamp": "2026-01-05T00:00:00+00:00",
                            "metadata": "not-an-object",
                        }
                    ],
                },
                "capture_time": "2026-01-05T00:00:01+00:00",
            }
        )


def test_capture_service_requires_message_timestamps() -> None:
    service = NanoMemService()
    with pytest.raises(ValueError, match=r"DialogueMessage\[0\].timestamp"):
        service.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                dialogue=CaptureDialogue(
                    occurred_at="2026-01-05T00:00:00+00:00",
                    messages=(
                        DialogueMessage(
                            role="user",
                            content="I prefer concise answers.",
                            timestamp="",
                        ),
                    ),
                ),
                capture_time="2026-01-05T00:00:01+00:00",
            )
        )


def test_capture_result_json_contract_round_trip() -> None:
    service = NanoMemService()
    result = service.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=CaptureDialogue(
                occurred_at="2026-01-05T00:00:00+00:00",
                messages=(
                    DialogueMessage(
                        role="user",
                        speaker_id="user-1",
                        content="I prefer concise Chinese answers.",
                        timestamp="2026-01-05T00:00:00+00:00",
                    ),
                ),
            ),
            capture_time="2026-01-05T00:00:01+00:00",
        )
    )

    payload = capture_result_to_json(result)

    assert set(payload) == {
        "dialogue_id",
        "accepted_message_count",
        "unit_count",
        "units",
        "skipped",
        "stats",
        "trace_ref",
    }
    assert payload["accepted_message_count"] == 1
    assert payload["unit_count"] == 1
    assert payload["units"][0]["scope"] == {
        "owner_id": "user-1",
        "namespace": "personal",
    }
    assert payload["units"][0]["dialogue_refs"][0]["message_range"] == [0, 1]

    parsed = capture_result_from_json(payload)
    assert parsed.dialogue_id == result.dialogue_id
    assert parsed.units[0].dialogue_refs[0].message_range == (0, 1)


def test_read_result_json_contract_round_trip() -> None:
    service = NanoMemService()
    service.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=CaptureDialogue(
                occurred_at="2026-01-05T00:00:00+00:00",
                messages=(
                    DialogueMessage(
                        role="user",
                        content="I prefer concise Chinese answers.",
                        timestamp="2026-01-05T00:00:00+00:00",
                    ),
                ),
            ),
            capture_time="2026-01-05T00:00:01+00:00",
        )
    )
    result = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=None,
            query="concise Chinese answers",
            query_time="2026-01-06T00:00:00+00:00",
            max_units=3,
            context_budget_tokens=80,
        )
    )

    payload = read_result_to_json(result)

    assert set(payload) == {
        "request",
        "ranked_units",
        "context",
        "stats",
        "trace_ref",
    }
    assert payload["request"]["owner_id"] == "user-1"
    assert payload["request"]["namespaces"] is None
    assert payload["context"]["unit_count"] == 1
    assert payload["context"]["token_count"] > 0
    assert "2026-01-05T00:00:00+00:00" in payload["context"]["text"]
    assert payload["ranked_units"][0]["unit"]["dialogue_refs"][0][
        "message_range"
    ] == [0, 1]
    assert payload["stats"]["returned_unit_count"] == 1
    assert payload["stats"]["index_backend"] == "dense_cosine_v1"

    parsed = read_result_from_json(payload)
    assert parsed.request.owner_id == "user-1"
    assert parsed.ranked_units[0].unit.text == "I prefer concise Chinese answers."
    assert parsed.context.unit_count == 1
