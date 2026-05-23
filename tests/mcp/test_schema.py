from __future__ import annotations

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


def test_mcp_capture_tool_schema_matches_public_contract() -> None:
    server = NanoMemMCPServer(NanoMemService())

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    tools = response["result"]["tools"]
    capture_tool = next(tool for tool in tools if tool["name"] == "nanomem_capture")
    schema = capture_tool["inputSchema"]
    assert schema["required"] == ["scope", "dialogue", "capture_time"]
    assert schema["properties"]["scope"]["required"] == ["owner_id"]
    assert schema["properties"]["dialogue"]["required"] == [
        "messages",
        "occurred_at",
    ]
    message_schema = schema["properties"]["dialogue"]["properties"]["messages"][
        "items"
    ]
    assert message_schema["required"] == ["role", "content", "timestamp"]
    assert "speaker_id" in message_schema["properties"]


def test_mcp_tool_calls_return_structured_public_results() -> None:
    server = NanoMemMCPServer(NanoMemService())

    capture = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nanomem_capture",
                "arguments": {
                    "scope": {"owner_id": "user-1", "namespace": "personal"},
                    "dialogue": {
                        "occurred_at": "2026-01-01T00:00:00+00:00",
                        "messages": [
                            {
                                "role": "user",
                                "content": "I prefer concise Chinese answers.",
                                "timestamp": "2026-01-01T00:00:00+00:00",
                            }
                        ],
                    },
                    "capture_time": "2026-01-01T00:00:01+00:00",
                },
            },
        }
    )
    assert capture is not None
    capture_payload = capture["result"]["structuredContent"]
    assert capture_payload["accepted_message_count"] == 1
    assert capture_payload["unit_count"] == 1
    assert capture_payload["units"][0]["scope"]["namespace"] == "personal"

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
