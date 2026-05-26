from __future__ import annotations

from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
)
from nanomem.mcp.server import NanoMemMCPServer
from nanomem.service.core import NanoMemService


def test_mcp_read_tool_schema_requires_query_time() -> None:
    server = NanoMemMCPServer(NanoMemService())

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    tools = response["result"]["tools"]
    read_tool = next(tool for tool in tools if tool["name"] == "nanomem_read")
    assert read_tool["inputSchema"]["required"] == [
        "owner_id",
        "query",
        "query_time",
    ]


def test_mcp_exposes_read_tool_only() -> None:
    server = NanoMemMCPServer(NanoMemService())

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    assert [tool["name"] for tool in response["result"]["tools"]] == ["nanomem_read"]


def test_mcp_tool_calls_return_structured_public_results() -> None:
    service = NanoMemService()
    service.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=CaptureDialogue(
                occurred_at="2026-01-01T00:00:00+00:00",
                messages=(
                    DialogueMessage(
                        role="user",
                        content="I prefer concise Chinese answers.",
                        timestamp="2026-01-01T00:00:00+00:00",
                    ),
                ),
            ),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )
    server = NanoMemMCPServer(service)

    read = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "nanomem_read",
                "arguments": {
                    "owner_id": "user-1",
                    "namespaces": None,
                    "query": "concise Chinese answers",
                    "query_time": "2026-01-02T00:00:00+00:00",
                },
            },
        }
    )
    assert read is not None
    read_payload = read["result"]["structuredContent"]
    assert read_payload["request"]["namespaces"] is None
    assert read_payload["context"]["unit_count"] == 1
    assert read_payload["ranked_units"][0]["unit"]["scope"]["owner_id"] == "user-1"


def test_mcp_rejects_capture_tool_calls() -> None:
    server = NanoMemMCPServer(NanoMemService())

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nanomem_capture",
                "arguments": {},
            },
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert response["error"]["message"] == "Unknown tool: nanomem_capture"
