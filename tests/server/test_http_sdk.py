from __future__ import annotations

import threading

import pytest

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
)
from nanomem.sdk import NanoMemClient
from nanomem.server.app import NanoMemHTTPServer
from nanomem.service.core import NanoMemService


def test_http_server_and_sdk_round_trip_capture_and_read() -> None:
    service = NanoMemService()
    try:
        server = NanoMemHTTPServer(("127.0.0.1", 0), service)
    except PermissionError as exc:
        pytest.skip(f"local socket bind is not available: {exc}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        client = NanoMemClient(f"http://{host}:{port}")

        assert client.health()["status"] == "ok"
        capture = client.capture(
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
        read = client.read(
            ReadRequest(
                owner_id="user-1",
                namespaces=None,
                query="concise Chinese answers",
                query_time="2026-01-02T00:00:00+00:00",
            )
        )

        assert capture.unit_count == 1
        assert len(read.ranked_units) == 1
        assert read.context.unit_count == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
