from __future__ import annotations

from nanomem.core.contracts import CaptureSkip, DialogueMessage


VISIBLE_ROLES = {"user", "assistant", "system_visible", "other"}


def is_extractable_message(message: DialogueMessage) -> bool:
    if message.role not in VISIBLE_ROLES:
        return False
    if not message.content.strip():
        return False
    if message.metadata.get("hidden") is True:
        return False
    if message.metadata.get("tool_call") is True:
        return False
    if message.metadata.get("tool_result") is True:
        return False
    return True


def is_assistant_reply(message: DialogueMessage) -> bool:
    return (
        message.role == "assistant"
        and message.metadata.get("is_final", True) is not False
    )


def non_extractable_message_skip(index: int, message: DialogueMessage) -> CaptureSkip:
    reason = "hidden_or_tool_message"
    if message.role not in VISIBLE_ROLES:
        reason = "invalid_role"
    elif not message.content.strip():
        reason = "empty_content"
    return CaptureSkip(
        message_range=(index, index + 1),
        reason=reason,
    )
