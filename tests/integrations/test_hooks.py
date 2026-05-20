from __future__ import annotations

from io import StringIO
import json
import threading

import pytest

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    MemoryUnitSelector,
)
from nanomem.integrations.hooks import HookConfig, run_capture, run_read
from nanomem.server.app import NanoMemHTTPServer
from nanomem.service.core import NanoMemService


def test_hook_read_injects_memory_context(tmp_path) -> None:
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
    with _server(service) as base_url:
        stdout = StringIO()
        code = run_read(
            HookConfig(
                host="codex",
                base_url=base_url,
                owner_id="user-1",
                namespace="personal",
                turn_dir=tmp_path,
            ),
            stdin=StringIO(
                json.dumps(
                    {
                        "session_id": "session-1",
                        "turn_id": "turn-1",
                        "prompt": "Please answer in my preferred style.",
                    }
                )
            ),
            stdout=stdout,
            stderr=StringIO(),
        )

    payload = json.loads(stdout.getvalue())
    assert code == 0
    assert payload["continue"] is True
    assert "concise Chinese answers" in payload["hookSpecificOutput"]["additionalContext"]
    assert len(tuple(tmp_path.glob("codex-*.json"))) == 1


def test_hook_capture_uses_spooled_prompt(tmp_path) -> None:
    service = NanoMemService()
    with _server(service) as base_url:
        config = HookConfig(
            host="claude-code",
            base_url=base_url,
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path,
        )
        run_read(
            config,
            stdin=StringIO(
                json.dumps(
                    {
                        "session_id": "session-1",
                        "prompt": "I prefer fact-level memory units.",
                    }
                )
            ),
            stdout=StringIO(),
            stderr=StringIO(),
        )
        stdout = StringIO()
        code = run_capture(
            config,
            stdin=StringIO(json.dumps({"session_id": "session-1"})),
            stdout=stdout,
            stderr=StringIO(),
        )

    units = service.store.query_units(
        MemoryUnitSelector(owner_id="user-1", namespaces=("personal",), limit=None)
    )
    assert code == 0
    assert json.loads(stdout.getvalue())["suppressOutput"] is True
    assert [unit.text for unit in units] == ["I prefer fact-level memory units."]


class _server:
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
