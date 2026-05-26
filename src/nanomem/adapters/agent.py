from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    CaptureResult,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
    ReadResult,
)
from nanomem.time import now_utc_iso


class NanoMemBackend(Protocol):
    def capture(self, request: CaptureRequest) -> CaptureResult:
        ...

    def read(self, request: ReadRequest) -> ReadResult:
        ...


@dataclass(frozen=True)
class AgentMessage:
    role: str
    content: str
    timestamp: str | None = None
    speaker_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentMemoryAdapter:
    """Map simple agent turn hooks onto NanoMem capture/read."""

    def __init__(
        self,
        backend: NanoMemBackend,
        scope: MemoryScope,
    ) -> None:
        self.backend = backend
        self.scope = scope

    def read(
        self,
        query: str | dict[str, Any],
        *,
        query_time: str | None = None,
        recency_policy: str = "balanced",
        max_units: int | None = None,
        context_budget_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReadResult:
        return self.backend.read(
            ReadRequest(
                owner_id=self.scope.owner_id,
                namespaces=(
                    None
                    if self.scope.namespace is None
                    else (self.scope.namespace,)
                ),
                query=query,
                query_time=query_time or now_utc_iso(),
                recency_policy=recency_policy,  # type: ignore[arg-type]
                max_units=max_units,
                context_budget_tokens=context_budget_tokens,
                metadata=dict(metadata or {}),
            )
        )

    def read_context(
        self,
        query: str | dict[str, Any],
        *,
        query_time: str | None = None,
        recency_policy: str = "balanced",
        max_units: int | None = None,
        context_budget_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.read(
            query,
            query_time=query_time,
            recency_policy=recency_policy,
            max_units=max_units,
            context_budget_tokens=context_budget_tokens,
            metadata=metadata,
        ).context.text

    def capture_messages(
        self,
        messages: Sequence[AgentMessage],
        *,
        session_id: str | None = None,
        capture_time: str | None = None,
        occurred_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CaptureResult:
        resolved_capture_time = capture_time or now_utc_iso()
        dialogue = CaptureDialogue(
            messages=tuple(
                DialogueMessage(
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp or resolved_capture_time,
                    speaker_id=message.speaker_id,
                    metadata=dict(message.metadata),
                )
                for message in messages
            ),
            occurred_at=occurred_at or resolved_capture_time,
            metadata=dict(metadata or {}),
        )
        return self.backend.capture(
            CaptureRequest(
                scope=self.scope,
                dialogue=dialogue,
                capture_time=resolved_capture_time,
                session_id=session_id or _metadata_session_id(metadata),
            )
        )

    def before_turn(
        self,
        user_message: str,
        *,
        query_time: str | None = None,
        recency_policy: str = "balanced",
        max_units: int | None = None,
        context_budget_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.read_context(
            user_message,
            query_time=query_time,
            recency_policy=recency_policy,
            max_units=max_units,
            context_budget_tokens=context_budget_tokens,
            metadata=metadata,
        )

    def after_turn(
        self,
        user_message: str,
        *,
        assistant_message: str | None = None,
        timestamp: str | None = None,
        capture_assistant: bool = False,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CaptureResult:
        resolved_time = timestamp or now_utc_iso()
        messages = [
            AgentMessage(
                role="user",
                content=user_message,
                timestamp=resolved_time,
                speaker_id=self.scope.owner_id,
                metadata=dict(metadata or {}),
            )
        ]
        if assistant_message is not None and capture_assistant:
            messages.append(
                AgentMessage(
                    role="assistant",
                    content=assistant_message,
                    timestamp=resolved_time,
                    speaker_id="agent",
                    metadata={
                        **dict(metadata or {}),
                        "message_kind": "reply",
                        "is_final": True,
                    },
                )
            )
        return self.capture_messages(
            messages,
            session_id=session_id,
            capture_time=resolved_time,
            occurred_at=resolved_time,
            metadata=metadata,
        )


def _metadata_session_id(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    value = metadata.get("session_id")
    return str(value) if value else None
