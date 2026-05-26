from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import threading

import pytest

from nanomem.core.config import config_from_mapping
from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    MemoryUnitSelector,
    OperationLogSelector,
    ReadRequest,
)
from nanomem.service.factory import service_from_config
from nanomem.integrations.hooks import (
    HookConfig,
    config_from_env,
    run_capture,
    run_read,
    run_spool,
)
from nanomem.transports.sdk import NanoMemClient
from nanomem.transports.http.app import NanoMemHTTPServer
from nanomem.service.core import NanoMemService


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "codex_hooks"


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
                        "prompt": "Please follow my concise Chinese answer preference.",
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
    assert tuple(tmp_path.glob("codex-*.json")) == ()


def test_hook_config_parses_flush_after_capture() -> None:
    config = config_from_env(
        "codex",
        {
            "NANOMEM_OWNER_ID": "user-1",
            "NANOMEM_FLUSH_AFTER_CAPTURE": "1",
        },
    )

    assert config.flush_after_capture is True


def test_hook_spool_records_prompt_without_reading_memory(tmp_path) -> None:
    stdout = StringIO()
    stderr = StringIO()
    code = run_spool(
        HookConfig(
            host="codex",
            base_url="http://127.0.0.1:1",
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path,
        ),
        stdin=StringIO(
            json.dumps(
                {
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "prompt": "Please decide whether memory is needed.",
                }
            )
        ),
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert code == 0
    assert payload == {"continue": True, "suppressOutput": True}
    assert stderr.getvalue() == ""
    assert len(tuple(tmp_path.glob("codex-*.json"))) == 1


def test_hook_read_mcp_trigger_does_not_read_or_spool(tmp_path) -> None:
    stdout = StringIO()
    stderr = StringIO()
    code = run_read(
        HookConfig(
            host="codex",
            base_url="http://127.0.0.1:1",
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path,
            read_trigger="mcp",
        ),
        stdin=StringIO(
            json.dumps(
                {
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "prompt": "Please decide whether memory is needed.",
                }
            )
        ),
        stdout=stdout,
        stderr=stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert code == 0
    assert payload == {"continue": True, "suppressOutput": True}
    assert stderr.getvalue() == ""
    assert tuple(tmp_path.glob("codex-*.json")) == ()


def test_hook_capture_skips_when_assistant_reply_is_missing(tmp_path) -> None:
    service = NanoMemService()
    with _server(service) as base_url:
        config = HookConfig(
            host="codex",
            base_url=base_url,
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path,
        )
        run_spool(
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
        stderr = StringIO()
        code = run_capture(
            config,
            stdin=StringIO(json.dumps({"session_id": "session-1"})),
            stdout=stdout,
            stderr=stderr,
        )

    units = service.store.query_units(
        MemoryUnitSelector(owner_id="user-1", namespaces=("personal",), limit=None)
    )
    assert code == 0
    assert json.loads(stdout.getvalue())["suppressOutput"] is True
    assert units == ()
    assert "assistant response is missing" in stderr.getvalue()


def test_hook_capture_can_opt_into_user_only_capture(tmp_path) -> None:
    service = NanoMemService()
    with _server(service) as base_url:
        config = HookConfig(
            host="codex",
            base_url=base_url,
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path,
            capture_assistant=False,
        )
        run_spool(
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


def test_hook_capture_records_assistant_reply_when_available(tmp_path) -> None:
    service = NanoMemService()
    with _server(service) as base_url:
        config = HookConfig(
            host="codex",
            base_url=base_url,
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path,
        )
        run_spool(
            config,
            stdin=StringIO(
                json.dumps(
                    {
                        "session_id": "session-1",
                        "turn_id": "turn-1",
                        "prompt": "I prefer concise Chinese answers.",
                    }
                )
            ),
            stdout=StringIO(),
            stderr=StringIO(),
        )
        code = run_capture(
            config,
            stdin=StringIO(
                json.dumps(
                    {
                        "session_id": "session-1",
                        "turn_id": "turn-1",
                        "last_assistant_message": "OK",
                    }
                )
            ),
            stdout=StringIO(),
            stderr=StringIO(),
        )

    logs = service.store.list_operation_logs(
        OperationLogSelector(owner_id="user-1", operation_type="capture")
    )
    dialogue_id = logs[0].summary["dialogue_id"]
    dialogue = service.store.get_dialogue(dialogue_id)
    assert code == 0
    assert dialogue is not None
    assert [message.role for message in dialogue.messages] == ["user", "assistant"]
    assert dialogue.messages[1].content == "OK"
    assert dialogue.messages[1].speaker_id == "agent"


def test_hook_capture_records_visible_user_assistant_message_list(tmp_path) -> None:
    service = NanoMemService()
    with _server(service) as base_url:
        code = run_capture(
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
                        "messages": [
                            {
                                "role": "user",
                                "content": "I prefer concise Chinese answers.",
                                "timestamp": "2026-01-01T00:00:00+00:00",
                            },
                            {
                                "role": "assistant",
                                "content": "I will inspect the project first.",
                                "timestamp": "2026-01-01T00:00:01+00:00",
                            },
                            {
                                "role": "tool",
                                "content": "pytest output hidden from memory",
                                "timestamp": "2026-01-01T00:00:02+00:00",
                            },
                            {
                                "role": "assistant",
                                "content": (
                                    "I will keep your preference for concise "
                                    "Chinese answers."
                                ),
                                "timestamp": "2026-01-01T00:00:03+00:00",
                            },
                        ],
                    }
                )
            ),
            stdout=StringIO(),
            stderr=StringIO(),
        )

    logs = service.store.list_operation_logs(
        OperationLogSelector(owner_id="user-1", operation_type="capture")
    )
    dialogue = service.store.get_dialogue(logs[0].summary["dialogue_id"])
    assert code == 0
    assert dialogue is not None
    assert [message.role for message in dialogue.messages] == [
        "user",
        "assistant",
        "assistant",
    ]
    assert dialogue.messages[1].content == "I will inspect the project first."
    assert dialogue.messages[2].speaker_id == "agent"


def test_hook_debug_dir_records_raw_hook_payload(tmp_path) -> None:
    stdout = StringIO()
    code = run_read(
        HookConfig(
            host="codex",
            base_url="http://127.0.0.1:1",
            owner_id="user-1",
            namespace="personal",
            turn_dir=tmp_path / "turns",
            debug_dir=tmp_path / "debug",
        ),
        stdin=StringIO(
            json.dumps(
                {
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                    "prompt": "Remember this debug shape.",
                }
            )
        ),
        stdout=stdout,
        stderr=StringIO(),
    )

    debug_files = tuple((tmp_path / "debug").glob("*.json"))
    debug_payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
    assert code == 0
    assert len(debug_files) == 1
    assert debug_payload["host"] == "codex"
    assert debug_payload["action"] == "read"
    assert debug_payload["payload"]["prompt"] == "Remember this debug shape."


def test_hook_debug_dir_does_not_overwrite_same_turn_payloads(tmp_path) -> None:
    config = HookConfig(
        host="codex",
        base_url="http://127.0.0.1:1",
        owner_id="user-1",
        namespace="personal",
        turn_dir=tmp_path / "turns",
        debug_dir=tmp_path / "debug",
    )
    payload = json.dumps(
        {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "prompt": "Remember this debug shape.",
        }
    )

    run_spool(config, stdin=StringIO(payload), stdout=StringIO(), stderr=StringIO())
    run_spool(config, stdin=StringIO(payload), stdout=StringIO(), stderr=StringIO())

    assert len(tuple((tmp_path / "debug").glob("*-codex-spool-*.json"))) == 2


def test_codex_sidecar_hook_flow_persists_across_restart(tmp_path) -> None:
    owner_id = "codex-user"
    namespace = "personal"
    config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(tmp_path / "nanomem.db"),
            },
            "index": {
                "backend": "dense",
            },
            "extraction": {
                "backend": "heuristic",
            },
        }
    )
    read_payload = _fixture("user_prompt_submit.json")
    stop_payload = _fixture("stop.json")

    service = service_from_config(config)
    try:
        with _server(service) as base_url:
            client = NanoMemClient(base_url)
            client.capture(
                CaptureRequest(
                    scope=MemoryScope(owner_id=owner_id, namespace=namespace),
                    dialogue=CaptureDialogue(
                        occurred_at="2026-05-24T09:00:00+08:00",
                        messages=(
                            DialogueMessage(
                                role="user",
                                speaker_id=owner_id,
                                content=(
                                    "I prefer concise Chinese answers for coding "
                                    "discussions."
                                ),
                                timestamp="2026-05-24T09:00:00+08:00",
                            ),
                        ),
                        metadata={"host": "seed"},
                    ),
                    capture_time="2026-05-24T09:00:01+08:00",
                )
            )

            hook_config = HookConfig(
                host="codex",
                base_url=base_url,
                owner_id=owner_id,
                namespace=namespace,
                turn_dir=tmp_path / "turns",
                debug_dir=tmp_path / "debug",
            )
            read_stdout = StringIO()
            spool_code = run_spool(
                hook_config,
                stdin=_stdin(read_payload),
                stdout=StringIO(),
                stderr=StringIO(),
            )
            read_code = run_read(
                hook_config,
                stdin=_stdin(read_payload),
                stdout=read_stdout,
                stderr=StringIO(),
            )
            read_output = json.loads(read_stdout.getvalue())

            capture_stdout = StringIO()
            capture_code = run_capture(
                hook_config,
                stdin=_stdin(stop_payload),
                stdout=capture_stdout,
                stderr=StringIO(),
            )

        logs = service.store.list_operation_logs(
            OperationLogSelector(
                owner_id=owner_id,
                namespaces=(namespace,),
                operation_type="capture",
            )
        )
        dialogues = tuple(
            service.store.get_dialogue(log.summary["dialogue_id"])
            for log in logs
        )
        captured_dialogue = next(
            (
                dialogue
                for dialogue in dialogues
                if dialogue is not None
                and [message.role for message in dialogue.messages]
                == ["user", "assistant"]
            ),
            None,
        )
    finally:
        service.store.close()  # type: ignore[attr-defined]

    assert read_code == 0
    assert spool_code == 0
    assert capture_code == 0
    assert "hookSpecificOutput" in read_output
    assert "concise Chinese answers" in read_output["hookSpecificOutput"][
        "additionalContext"
    ]
    assert json.loads(capture_stdout.getvalue())["continue"] is True
    assert captured_dialogue is not None
    assert [message.role for message in captured_dialogue.messages] == [
        "user",
        "assistant",
    ]
    assert captured_dialogue.messages[0].content == read_payload["prompt"]
    assert captured_dialogue.messages[1].content == stop_payload[
        "last_assistant_message"
    ]
    assert len(tuple((tmp_path / "debug").glob("*-codex-read-*.json"))) == 1
    assert len(tuple((tmp_path / "debug").glob("*-codex-capture-*.json"))) == 1

    restarted = service_from_config(config)
    try:
        with _server(restarted) as base_url:
            read = NanoMemClient(base_url).read(
                ReadRequest(
                    owner_id=owner_id,
                    namespaces=(namespace,),
                    query="sidecar flow concise Chinese answer preference",
                    query_time="2026-05-24T09:05:00+08:00",
                    max_units=5,
                )
            )
    finally:
        restarted.store.close()  # type: ignore[attr-defined]

    texts = [ranked.unit.text for ranked in read.ranked_units]
    assert read.context.unit_count >= 1
    assert any("sidecar flow" in text for text in texts)
    assert any("concise Chinese answers" in text for text in texts)


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


def _fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _stdin(payload: dict) -> StringIO:
    return StringIO(json.dumps(payload))
