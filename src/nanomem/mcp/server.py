from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any, TextIO

from nanomem.contracts import CaptureRequest, ReadRequest
from nanomem.serde import capture_request_from_json, read_request_from_json
from nanomem.service.core import NanoMemService


JSONRPC_VERSION = "2.0"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"


class NanoMemMCPServer:
    """Dependency-free MCP stdio server exposing NanoMem capture/read tools."""

    def __init__(
        self,
        service: NanoMemService,
        *,
        name: str = "nanomem",
        version: str = "0.1.0",
    ) -> None:
        self.service = service
        self.name = name
        self.version = version

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        request_id = message.get("id")
        method = message.get("method")
        if not method:
            return _error(request_id, -32600, "Invalid Request")
        try:
            if method == "initialize":
                return _result(request_id, self._initialize(message.get("params")))
            if method == "ping":
                return _result(request_id, {})
            if method == "tools/list":
                return _result(request_id, {"tools": _tools()})
            if method == "tools/call":
                return _result(request_id, self._call_tool(message.get("params")))
            if method.startswith("notifications/"):
                return None
            return _error(request_id, -32601, f"Method not found: {method}")
        except ValueError as exc:
            return _error(request_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover - safety net
            return _error(request_id, -32000, str(exc))

    def _initialize(self, params: object) -> dict[str, Any]:
        payload = params if isinstance(params, dict) else {}
        return {
            "protocolVersion": str(
                payload.get("protocolVersion", DEFAULT_PROTOCOL_VERSION)
            ),
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            },
        }

    def _call_tool(self, params: object) -> dict[str, Any]:
        payload = _mapping(params)
        name = str(payload.get("name", ""))
        arguments = _mapping(payload.get("arguments"))
        if name == "nanomem_read":
            return _tool_result(self._read(arguments))
        if name == "nanomem_capture":
            return _tool_result(self._capture(arguments))
        raise ValueError(f"Unknown tool: {name}")

    def _read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        request = read_request_from_json(arguments)
        result = self.service.read(request)
        return asdict(result)

    def _capture(self, arguments: dict[str, Any]) -> dict[str, Any]:
        request = capture_request_from_json(arguments)
        result = self.service.capture(request)
        return asdict(result)


def run_stdio(
    server: NanoMemMCPServer,
    *,
    input_stream: TextIO,
    output_stream: TextIO,
) -> None:
    for line in input_stream:
        text = line.strip()
        if not text:
            continue
        try:
            message = json.loads(text)
        except json.JSONDecodeError as exc:
            response = _error(None, -32700, f"Parse error: {exc.msg}")
        else:
            if not isinstance(message, dict):
                response = _error(None, -32600, "Invalid Request")
            else:
                response = server.handle(message)
        if response is None:
            continue
        output_stream.write(json.dumps(response, ensure_ascii=False, sort_keys=True))
        output_stream.write("\n")
        output_stream.flush()


def _tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "nanomem_read",
            "description": (
                "Read relevant long-term personal memory units from NanoMem. "
                "Use this before answering when user-specific context may matter."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "owner_id": {"type": "string"},
                    "namespaces": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                    },
                    "query": {
                        "type": ["string", "object"],
                        "description": "Search query or structured read query.",
                    },
                    "query_time": {
                        "type": ["string", "null"],
                    },
                    "time_range": _time_range_schema(),
                    "recency_policy": {
                        "type": "string",
                        "enum": ["recent", "balanced", "historical"],
                        "default": "balanced",
                    },
                    "max_units": {
                        "type": ["integer", "null"],
                    },
                    "context_budget_tokens": {
                        "type": ["integer", "null"],
                    },
                    "metadata": {
                        "type": "object",
                    },
                },
                "required": ["owner_id", "query", "query_time"],
            },
        },
        {
            "name": "nanomem_capture",
            "description": (
                "Capture user-visible dialogue into NanoMem long-term personal "
                "memory. Do not send hidden reasoning, tool logs, code docs, "
                "or workspace-local content."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scope": _scope_schema(),
                    "dialogue": _capture_dialogue_schema(),
                    "capture_time": {
                        "type": "string",
                    },
                    "options": {
                        "type": "object",
                        "description": "Capture options such as chunk_size.",
                    },
                },
                "required": ["scope", "dialogue", "capture_time"],
            },
        },
    ]


def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return {
        "content": [
            {
                "type": "text",
                "text": text,
            }
        ],
        "structuredContent": payload,
    }


def _scope_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "owner_id": {"type": "string"},
            "namespace": {"type": ["string", "null"]},
        },
        "required": ["owner_id"],
    }


def _capture_dialogue_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "items": _dialogue_message_schema(),
            },
            "occurred_at": {"type": "string"},
            "metadata": {"type": "object"},
        },
        "required": ["messages", "occurred_at"],
    }


def _time_range_schema() -> dict[str, Any]:
    return {
        "type": ["object", "null"],
        "properties": {
            "start": {"type": ["string", "null"]},
            "end": {"type": ["string", "null"]},
        },
    }


def _dialogue_message_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "description": "Usually user or assistant.",
            },
            "content": {"type": "string"},
            "timestamp": {"type": "string"},
            "speaker_id": {"type": ["string", "null"]},
            "metadata": {"type": "object"},
        },
        "required": ["role", "content", "timestamp"],
    }


def _mapping(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected object, got {type(value).__name__}")
    return value


def _result(request_id: object, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "result": result,
    }


def _error(
    request_id: object,
    code: int,
    message: str,
) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
