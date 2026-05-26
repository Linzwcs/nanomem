from __future__ import annotations

import argparse
from dataclasses import dataclass
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, TextIO
import uuid

from nanomem.adapters.agent import AgentMemoryAdapter, AgentMessage
from nanomem.core.contracts import FlushRequest, MemoryScope
from nanomem.transports.sdk import NanoMemClient, NanoMemClientError
from nanomem.core.time import now_utc_iso


DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_MAX_UNITS = 8
DEFAULT_CONTEXT_BUDGET_TOKENS = 1200


@dataclass(frozen=True)
class HookConfig:
    host: str
    base_url: str = DEFAULT_BASE_URL
    owner_id: str = ""
    namespace: str | None = None
    max_units: int = DEFAULT_MAX_UNITS
    context_budget_tokens: int = DEFAULT_CONTEXT_BUDGET_TOKENS
    recency_policy: str = "balanced"
    turn_dir: Path = Path(".nanomem/agent-turns")
    debug_dir: Path | None = None
    timeout: float = 5.0
    capture_assistant: bool = True
    read_trigger: str = "submit"
    flush_after_capture: bool = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nanomem-agent-hook")
    parser.add_argument("action", choices=("spool", "read", "capture"))
    parser.add_argument("--host", required=True, help="Host harness name.")
    args = parser.parse_args(argv)
    config = config_from_env(args.host)
    if args.action == "spool":
        return run_spool(config)
    if args.action == "read":
        return run_read(config)
    return run_capture(config)


def config_from_env(host: str, env: dict[str, str] | None = None) -> HookConfig:
    values = env if env is not None else os.environ
    namespace = values.get("NANOMEM_NAMESPACE")
    if namespace == "":
        namespace = None
    return HookConfig(
        host=host,
        base_url=values.get("NANOMEM_BASE_URL", DEFAULT_BASE_URL),
        owner_id=values.get("NANOMEM_OWNER_ID", getpass.getuser()),
        namespace=namespace,
        max_units=_int_env(values, "NANOMEM_MAX_UNITS", DEFAULT_MAX_UNITS),
        context_budget_tokens=_int_env(
            values,
            "NANOMEM_CONTEXT_BUDGET_TOKENS",
            DEFAULT_CONTEXT_BUDGET_TOKENS,
        ),
        recency_policy=values.get("NANOMEM_RECENCY_POLICY", "balanced"),
        turn_dir=Path(values.get("NANOMEM_TURN_DIR", ".nanomem/agent-turns")),
        debug_dir=_optional_path(values.get("NANOMEM_HOOK_DEBUG_DIR")),
        timeout=float(values.get("NANOMEM_TIMEOUT", "5")),
        capture_assistant=_bool_env(
            values,
            "NANOMEM_CAPTURE_ASSISTANT",
            default=True,
        ),
        read_trigger=values.get("NANOMEM_READ_TRIGGER", "submit").strip().lower(),
        flush_after_capture=_bool_env(
            values,
            "NANOMEM_FLUSH_AFTER_CAPTURE",
            default=False,
        ),
    )


def run_spool(
    config: HookConfig,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    payload = _read_payload(stdin, stderr)
    _write_debug_payload(config, payload, action="spool", stderr=stderr)
    prompt = _extract_user_prompt(payload)
    if prompt:
        _write_turn(config, payload, prompt)
    _write_json(stdout, _success_response())
    return 0


def run_read(
    config: HookConfig,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    payload = _read_payload(stdin, stderr)
    _write_debug_payload(config, payload, action="read", stderr=stderr)
    prompt = _extract_user_prompt(payload)
    if not prompt:
        _write_json(stdout, _success_response())
        return 0

    if config.read_trigger == "mcp":
        _write_json(stdout, _success_response())
        return 0
    if config.read_trigger != "submit":
        _log(stderr, f"unsupported NANOMEM_READ_TRIGGER={config.read_trigger}")
        _write_json(stdout, _success_response())
        return 0
    try:
        adapter = _adapter(config)
        context = adapter.before_turn(
            prompt,
            max_units=config.max_units,
            context_budget_tokens=config.context_budget_tokens,
            recency_policy=config.recency_policy,
            metadata=_metadata(config, payload, operation="hook_read"),
        )
    except (NanoMemClientError, OSError, ValueError) as exc:
        _log(stderr, f"nanomem read failed: {exc}")
        _write_json(stdout, _success_response())
        return 0

    context = context.strip()
    if not context:
        _write_json(stdout, _success_response())
        return 0
    _write_json(stdout, _context_response(_memory_block(context)))
    return 0


def run_capture(
    config: HookConfig,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    payload = _read_payload(stdin, stderr)
    _write_debug_payload(config, payload, action="capture", stderr=stderr)
    turn = _read_turn(config, payload)
    prompt = _extract_user_prompt(payload) or turn.get("prompt")
    messages = _extract_capture_messages(
        config,
        payload=payload,
        turn=turn,
        prompt=prompt if isinstance(prompt, str) else None,
    )
    if not messages:
        if config.capture_assistant and prompt:
            _log(stderr, "nanomem capture skipped: assistant response is missing")
        _write_json(stdout, _success_response())
        return 0

    if config.capture_assistant and not any(
        message.role == "assistant" for message in messages
    ):
        _log(stderr, "nanomem capture skipped: assistant response is missing")
        _write_json(stdout, _success_response())
        return 0
    try:
        client = NanoMemClient(config.base_url, timeout=config.timeout)
        adapter = AgentMemoryAdapter(
            client,
            MemoryScope(owner_id=config.owner_id, namespace=config.namespace),
        )
        metadata = _metadata(config, payload, operation="hook_capture")
        adapter.capture_messages(
            tuple(messages),
            metadata=metadata,
        )
        session_id = metadata.get("session_id")
        if config.flush_after_capture and session_id:
            client.flush(
                FlushRequest(
                    scope=MemoryScope(
                        owner_id=config.owner_id,
                        namespace=config.namespace,
                    ),
                    session_id=str(session_id),
                )
            )
    except (NanoMemClientError, OSError, ValueError) as exc:
        _log(stderr, f"nanomem capture failed: {exc}")
        _write_json(stdout, _success_response())
        return 0

    _write_json(stdout, _success_response())
    return 0


def _adapter(config: HookConfig) -> AgentMemoryAdapter:
    return AgentMemoryAdapter(
        NanoMemClient(config.base_url, timeout=config.timeout),
        MemoryScope(owner_id=config.owner_id, namespace=config.namespace),
    )


def _read_payload(stdin: TextIO, stderr: TextIO) -> dict[str, Any]:
    raw = stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        _log(stderr, f"invalid hook JSON input: {exc.msg}")
        return {}
    if not isinstance(payload, dict):
        _log(stderr, "hook JSON input must be an object")
        return {}
    return payload


def _extract_user_prompt(payload: dict[str, Any]) -> str | None:
    return _first_text(
        payload,
        (
            ("prompt",),
            ("user_prompt",),
            ("userPrompt",),
            ("message",),
            ("input", "prompt"),
            ("input", "message"),
            ("hook_input", "prompt"),
            ("hookInput", "prompt"),
        ),
    )


def _extract_assistant_message(payload: dict[str, Any]) -> str | None:
    return _first_text(
        payload,
        (
            ("assistant_message",),
            ("assistantMessage",),
            ("assistant_response",),
            ("assistantResponse",),
            ("last_assistant_message",),
            ("lastAssistantMessage",),
            ("response",),
            ("output", "text"),
            ("output", "content"),
        ),
    )


def _extract_capture_messages(
    config: HookConfig,
    *,
    payload: dict[str, Any],
    turn: dict[str, Any],
    prompt: str | None,
) -> list[AgentMessage]:
    explicit = _extract_explicit_messages(config, payload)
    if explicit:
        if prompt and not any(message.role == "user" for message in explicit):
            explicit.insert(
                0,
                AgentMessage(
                    role="user",
                    content=prompt,
                    speaker_id=config.owner_id,
                ),
            )
        if not config.capture_assistant:
            return [message for message in explicit if message.role == "user"]
        return explicit

    if not prompt:
        return []
    assistant_message = _extract_assistant_message(payload)
    if config.capture_assistant and assistant_message is not None:
        return [
            AgentMessage(
                role="user",
                content=prompt,
                speaker_id=config.owner_id,
            ),
            AgentMessage(
                role="assistant",
                content=assistant_message,
                speaker_id="agent",
                metadata={
                    "message_kind": "reply",
                    "is_final": True,
                },
            ),
        ]
    if not config.capture_assistant:
        return [
            AgentMessage(
                role="user",
                content=prompt,
                speaker_id=config.owner_id,
            )
        ]
    return []


def _extract_explicit_messages(
    config: HookConfig,
    payload: dict[str, Any],
) -> list[AgentMessage]:
    raw = _first_list(
        payload,
        (
            ("messages",),
            ("transcript",),
            ("conversation",),
            ("dialogue", "messages"),
            ("input", "messages"),
            ("hook_input", "messages"),
            ("hookInput", "messages"),
            ("output", "messages"),
        ),
    )
    if raw is None:
        return []
    messages: list[AgentMessage] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = _visible_role(item)
        if role is None:
            continue
        content = _message_content(item)
        if content is None:
            continue
        messages.append(
            AgentMessage(
                role=role,
                content=content,
                timestamp=_optional_text(
                    item.get("timestamp")
                    or item.get("created_at")
                    or item.get("createdAt")
                ),
                speaker_id=_speaker_id(config, item, role),
                metadata=_message_metadata(item, role),
            )
        )
    return messages


def _first_text(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> str | None:
    for path in paths:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_list(
    payload: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> list[Any] | None:
    for path in paths:
        value: Any = payload
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if isinstance(value, list):
            return value
    return None


def _visible_role(item: dict[str, Any]) -> str | None:
    role = _optional_text(item.get("role") or item.get("speaker"))
    if role is None:
        return None
    role = role.lower()
    if role in {"user", "assistant"}:
        return role
    return None


def _message_content(item: dict[str, Any]) -> str | None:
    value = (
        item.get("content")
        or item.get("text")
        or item.get("message")
        or item.get("output")
    )
    text = _text_from_value(value)
    return text if text and text.strip() else None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [
            part
            for item in value
            if (part := _text_from_value(item))
        ]
        return "\n".join(parts).strip() if parts else None
    if isinstance(value, dict):
        return _text_from_value(value.get("text") or value.get("content"))
    return None


def _speaker_id(config: HookConfig, item: dict[str, Any], role: str) -> str:
    value = _optional_text(item.get("speaker_id") or item.get("speakerId"))
    if value is not None:
        return value
    return config.owner_id if role == "user" else "agent"


def _message_metadata(item: dict[str, Any], role: str) -> dict[str, Any]:
    metadata = item.get("metadata")
    data = dict(metadata) if isinstance(metadata, dict) else {}
    if role == "assistant":
        data.setdefault("message_kind", "reply")
    return data


def _optional_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _write_turn(
    config: HookConfig,
    payload: dict[str, Any],
    prompt: str,
) -> None:
    config.turn_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "host": config.host,
        "prompt": prompt,
        "created_at": now_utc_iso(),
        "input": payload,
    }
    _turn_path(config, payload).write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _read_turn(config: HookConfig, payload: dict[str, Any]) -> dict[str, Any]:
    path = _turn_path(config, payload)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_debug_payload(
    config: HookConfig,
    payload: dict[str, Any],
    *,
    action: str,
    stderr: TextIO,
) -> None:
    if config.debug_dir is None:
        return
    try:
        config.debug_dir.mkdir(parents=True, exist_ok=True)
        path = config.debug_dir / (
            f"{now_utc_iso().replace(':', '').replace('+', 'Z')}-"
            f"{config.host}-{action}-{_turn_key(payload)}-"
            f"{uuid.uuid4().hex[:8]}.json"
        )
        path.write_text(
            json.dumps(
                {
                    "host": config.host,
                    "action": action,
                    "captured_at": now_utc_iso(),
                    "payload": payload,
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        _log(stderr, f"failed to write hook debug payload: {exc}")


def _turn_path(config: HookConfig, payload: dict[str, Any]) -> Path:
    return config.turn_dir / f"{config.host}-{_turn_key(payload)}.json"


def _turn_key(payload: dict[str, Any]) -> str:
    parts = [
        str(payload.get("turn_id") or payload.get("turnId") or ""),
        str(payload.get("session_id") or payload.get("sessionId") or ""),
        str(payload.get("conversation_id") or payload.get("conversationId") or ""),
        str(payload.get("transcript_path") or payload.get("transcriptPath") or ""),
        str(payload.get("cwd") or ""),
    ]
    if not any(parts):
        parts.append("default")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:24]


def _metadata(
    config: HookConfig,
    payload: dict[str, Any],
    *,
    operation: str,
) -> dict[str, Any]:
    return {
        "adapter": config.host,
        "operation": operation,
        "session_id": payload.get("session_id") or payload.get("sessionId"),
        "turn_id": payload.get("turn_id") or payload.get("turnId"),
        "cwd": payload.get("cwd"),
    }


def _success_response() -> dict[str, Any]:
    return {
        "continue": True,
        "suppressOutput": True,
    }


def _context_response(context: str) -> dict[str, Any]:
    return {
        **_success_response(),
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }


def _memory_block(context: str) -> str:
    return (
        "<nanomem_personal_memory>\n"
        "Relevant long-term personal memory:\n"
        f"{context}\n"
        "</nanomem_personal_memory>"
    )


def _write_json(stdout: TextIO, payload: dict[str, Any]) -> None:
    stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    stdout.write("\n")
    stdout.flush()


def _log(stderr: TextIO, message: str) -> None:
    stderr.write(f"[nanomem] {message}\n")
    stderr.flush()


def _int_env(values: dict[str, str], key: str, default: int) -> int:
    value = values.get(key)
    if value is None or value == "":
        return default
    return int(value)


def _bool_env(values: dict[str, str], key: str, *, default: bool = False) -> bool:
    value = values.get(key)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _optional_path(value: str | None) -> Path | None:
    if value is None or value == "":
        return None
    return Path(value)


if __name__ == "__main__":
    raise SystemExit(main())
