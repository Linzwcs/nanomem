from __future__ import annotations

from typing import Any

from nanomem.contracts import (
    Dialogue,
    DialogueMessage,
    ExtractionRequest,
    MemoryScope,
)
from nanomem.extraction.llm import (
    LLMMemoryUnitExtractor,
    LLM_EXTRACTION_PROMPT,
)
from nanomem.extraction.prompts import (
    ALLOWED_MEMORY_TYPES,
    LLM_EXTRACTION_PROMPT_VERSION,
)


class _FakeCompletionClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        model: str,
        messages: tuple[dict[str, str], ...],
    ) -> dict[str, Any]:
        self.calls.append({"model": model, "messages": messages})
        return self.payload


def _request() -> ExtractionRequest:
    occurred_at = "2026-01-01T00:00:00+00:00"
    dialogue = Dialogue(
        dialogue_id="dlg-1",
        session_id=None,
        messages=(
            DialogueMessage(
                role="user",
                content="I prefer concise Chinese answers.",
                timestamp=occurred_at,
            ),
        ),
        started_at=occurred_at,
        ended_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    return ExtractionRequest(
        scope=MemoryScope(owner_id="user-1", namespace="personal"),
        dialogue=dialogue,
        extraction_time="2026-01-01T00:00:01+00:00",
    )


def test_extracted_unit_records_prompt_version_in_metadata() -> None:
    client = _FakeCompletionClient(
        payload={
            "units": [
                {
                    "text": "The user prefers concise Chinese answers.",
                    "memory_type": "preference",
                    "message_range": None,
                }
            ],
            "skipped": [],
        }
    )
    extractor = LLMMemoryUnitExtractor(
        model="fake-model",
        api_key="fake",
        completion_client=client,
    )

    result = extractor.extract(_request())

    assert len(result.units) == 1
    metadata = result.units[0].metadata
    assert metadata["prompt_version"] == LLM_EXTRACTION_PROMPT_VERSION


def test_prompt_is_used_in_system_message() -> None:
    client = _FakeCompletionClient(payload={"units": [], "skipped": []})
    extractor = LLMMemoryUnitExtractor(
        model="fake-model",
        api_key="fake",
        completion_client=client,
    )

    extractor.extract(_request())

    assert len(client.calls) == 1
    system_messages = [
        msg for msg in client.calls[0]["messages"] if msg["role"] == "system"
    ]
    assert system_messages
    assert system_messages[0]["content"] == LLM_EXTRACTION_PROMPT


def test_allowed_memory_types_includes_paper_vocabulary() -> None:
    # Sanity: vocabulary in prompts.py must cover what the prompt advertises.
    expected = {
        "preference",
        "correction",
        "habit",
        "background",
        "relationship",
        "user_event",
        "agent_interaction_event",
        "uncertain",
    }
    assert expected.issubset(ALLOWED_MEMORY_TYPES)


def test_prompt_is_reimported_from_llm_module_for_backward_compat() -> None:
    # External code that imported the prompt from extraction.llm should
    # continue to work after the move.
    from nanomem.extraction import llm as llm_module
    from nanomem.extraction import prompts as prompts_module

    assert llm_module.LLM_EXTRACTION_PROMPT is prompts_module.LLM_EXTRACTION_PROMPT
    assert llm_module.ALLOWED_MEMORY_TYPES is prompts_module.ALLOWED_MEMORY_TYPES
