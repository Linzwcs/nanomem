from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    FlushRequest,
    MemoryScope,
    ReadRequest,
)
from nanomem.sdk import NanoMemClient, NanoMemClientError
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


def test_http_sdk_flushes_session_buffer() -> None:
    with _RunningServer(NanoMemService()) as base_url:
        client = NanoMemClient(base_url)
        capture = client.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                session_id="session-1",
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
        flushed = client.flush(
            FlushRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                session_id="session-1",
            )
        )

        assert capture.unit_count == 0
        assert flushed.dialogue_count == 1
        assert flushed.unit_count == 1


def test_http_contract_rejects_missing_capture_timestamp() -> None:
    with _RunningServer(NanoMemService()) as base_url:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(
                f"{base_url}/v1/capture",
                {
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
                },
            )

        assert exc_info.value.code == 400
        assert "CaptureRequest.capture_time is required" in (
            exc_info.value.read().decode("utf-8")
        )


def test_sdk_surfaces_http_contract_errors() -> None:
    with _RunningServer(NanoMemService()) as base_url:
        client = NanoMemClient(base_url)

        with pytest.raises(NanoMemClientError) as exc_info:
            client.read(
                ReadRequest(
                    owner_id="",
                    namespaces=None,
                    query="answer style",
                    query_time="2026-01-02T00:00:00+00:00",
                )
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.payload["error"] == "bad_request"
        assert "ReadRequest.owner_id is required" in str(exc_info.value)


class _RunningServer:
    def __init__(self, service: NanoMemService) -> None:
        self.service = service
        self.server: NanoMemHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> str:
        try:
            self.server = NanoMemHTTPServer(("127.0.0.1", 0), self.service)
        except PermissionError as exc:
            pytest.skip(f"local socket bind is not available: {exc}")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        assert self.server is not None
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=_json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")
