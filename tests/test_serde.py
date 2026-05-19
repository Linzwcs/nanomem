from __future__ import annotations

import pytest

from nanomem.serde import capture_request_from_json, read_request_from_json


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
