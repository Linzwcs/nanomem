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
