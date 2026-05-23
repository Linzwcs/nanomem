from __future__ import annotations

import json
from typing import Any

from nanomem.contracts import (
    DialogueMessage,
    DialogueRecord,
    ExtractionRequest,
    MemoryScope,
)
from nanomem.extraction.llm import LLMMemoryUnitExtractor


class ScriptedCompletionClient:
    def __init__(self, responses: tuple[dict[str, Any], ...]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
    ) -> dict[str, Any]:
        call_index = len(self.calls)
        self.calls.append({"model": model, "messages": messages})
        return self.responses[call_index]


def test_llm_behavior_fixtures_cover_core_user_memory_types() -> None:
    client = ScriptedCompletionClient(
        (
            {
                "units": [
                    {
                        "text": "The user said they prefer concise Chinese answers.",
                        "message_range": [0, 1],
                        "memory_type": "preference",
                    },
                    {
                        "text": "The user corrected the agent not to auto-commit code unless asked.",
                        "message_range": [1, 2],
                        "memory_type": "correction",
                    }
                ],
                "skipped": [],
            },
            {
                "units": [
                    {
                        "text": "The user said they joined the NanoMem design review on May 6, 2026.",
                        "message_range": [2, 3],
                        "memory_type": "user_event",
                    }
                ],
                "skipped": [],
            },
        )
    )
    result = _extract(
        client,
        (
            _message("user", "I prefer concise Chinese answers.", 0),
            _message("user", "Do not auto-commit code unless I ask.", 1),
            _message("user", "I joined the NanoMem design review on May 6, 2026.", 2),
        ),
    )

    assert [(unit.memory_type, unit.text) for unit in result.units] == [
        ("preference", "The user said they prefer concise Chinese answers."),
        (
            "correction",
            "The user corrected the agent not to auto-commit code unless asked.",
        ),
        (
            "user_event",
            "The user said they joined the NanoMem design review on May 6, 2026.",
        ),
    ]
    assert [unit.dialogue_refs[0].message_range for unit in result.units] == [
        (0, 1),
        (1, 2),
        (2, 3),
    ]
    assert result.stats["chunk_count"] == 2


def test_llm_behavior_fixture_captures_agent_interaction_event() -> None:
    client = ScriptedCompletionClient(
        (
            {
                "units": [
                    {
                        "text": "The agent said it will remember that the user prefers concise Chinese answers in future sessions.",
                        "message_range": [0, 1],
                        "memory_type": "agent_interaction_event",
                    }
                ],
                "skipped": [],
            },
        )
    )
    result = _extract(
        client,
        (
            _message(
                "assistant",
                "I will remember that you prefer concise Chinese answers in future sessions.",
                0,
            ),
        ),
    )

    assert result.units[0].memory_type == "agent_interaction_event"
    assert result.units[0].text == (
        "The agent said it will remember that the user prefers concise "
        "Chinese answers in future sessions."
    )
    assert result.units[0].dialogue_refs[0].message_range == (0, 1)


def test_llm_behavior_fixture_preserves_multi_turn_attribution() -> None:
    client = ScriptedCompletionClient(
        (
            {
                "units": [
                    {
                        "text": "The user corrected the agent not to auto-commit code.",
                        "message_range": [0, 2],
                        "memory_type": "correction",
                    }
                ],
                "skipped": [],
            },
        )
    )
    result = _extract(
        client,
        (
            _message("user", "Do not auto-commit code.", 0),
            _message("assistant", "Understood. I will wait for explicit permission.", 1),
        ),
    )

    unit = result.units[0]
    assert unit.text == "The user corrected the agent not to auto-commit code."
    assert unit.dialogue_refs[0].message_range == (0, 2)
    assert unit.timestamp == "2026-01-01T00:00:10+00:00"
    assert _sent_indexes(client) == [[0, 1]]


def test_llm_behavior_fixture_skips_workspace_and_tool_logs() -> None:
    client = ScriptedCompletionClient(
        (
            {
                "units": [],
                "skipped": [
                    {
                        "message_range": [0, 1],
                        "reason": "workspace_fact",
                        "detail": "workspace file content is not personal memory",
                    }
                ],
            },
        )
    )
    result = _extract(
        client,
        (
            _message("user", "README.md says the server command is nanomem-server.", 0),
            _message("tool", "pytest output: 13 passed, 1 skipped.", 1),
        ),
    )

    assert result.units == ()
    assert sorted(skip.reason for skip in result.skipped) == [
        "invalid_role",
        "workspace_fact",
    ]
    assert _sent_indexes(client) == [[0]]


def _extract(
    client: ScriptedCompletionClient,
    messages: tuple[DialogueMessage, ...],
) -> Any:
    extractor = LLMMemoryUnitExtractor(
        model="test-model",
        completion_client=client,
        max_messages_per_chunk=2,
    )
    return extractor.extract(
        ExtractionRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=DialogueRecord(
                dialogue_id="dlg-1",
                messages=messages,
                captured_at="2026-01-01T00:00:40+00:00",
                occurred_at="2026-01-01T00:00:00+00:00",
            ),
        )
    )


def _sent_indexes(client: ScriptedCompletionClient) -> list[list[int]]:
    return [
        [
            message["index"]
            for message in json.loads(call["messages"][1]["content"])["messages"]
        ]
        for call in client.calls
    ]


def _message(role: str, content: str, offset: int) -> DialogueMessage:
    return DialogueMessage(
        role=role,
        content=content,
        timestamp=f"2026-01-01T00:00:{offset * 10:02d}+00:00",
        speaker_id="user-1" if role == "user" else role,
    )
