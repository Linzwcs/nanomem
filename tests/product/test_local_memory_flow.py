from __future__ import annotations

import json

from nanomem.core.config import config_from_mapping
from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueWindowSelector,
    DialogueMessage,
    FlushRequest,
    MemoryScope,
    ReadRequest,
    TimeRange,
)
from nanomem.service.factory import service_from_config
from nanomem.server.manager import handle_manager_get, handle_manager_post


def test_local_product_flow_persists_rebuilds_reads_renders_and_audits(
    tmp_path,
) -> None:
    config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(tmp_path / "nanomem.db"),
            },
            "index": {
                "backend": "dense",
                "rebuild_on_startup": True,
            },
            "read": {
                "default_max_units": 5,
            },
        }
    )
    writer = service_from_config(config)
    first_capture = writer.capture(
        _capture_request(
            owner_id="user-1",
            namespace="personal",
            occurred_at="2026-01-01T10:00:00+00:00",
            capture_time="2026-01-01T10:00:03+00:00",
            messages=(
                DialogueMessage(
                    role="assistant",
                    content="What should I remember?",
                    timestamp="2026-01-01T10:00:00+00:00",
                    speaker_id="agent",
                ),
                DialogueMessage(
                    role="user",
                    content=(
                        "I prefer concise Chinese answers. "
                        "I usually want design tradeoffs before implementation."
                    ),
                    timestamp="2026-01-01T10:00:01+00:00",
                    speaker_id="user-1",
                ),
            ),
        )
    )
    second_capture = writer.capture(
        _capture_request(
            owner_id="user-1",
            namespace="work",
            occurred_at="2026-01-02T09:00:00+00:00",
            capture_time="2026-01-02T09:00:01+00:00",
            messages=(
                DialogueMessage(
                    role="user",
                    content="I prefer local-first memory storage for NanoMem.",
                    timestamp="2026-01-02T09:00:00+00:00",
                    speaker_id="user-1",
                ),
            ),
        )
    )

    assert first_capture.unit_count == 2
    assert second_capture.unit_count == 1
    assert writer.index.document_count() == 3  # type: ignore[attr-defined]
    writer.store.close()  # type: ignore[attr-defined]

    service = service_from_config(config)

    assert service.index.document_count() == 3  # type: ignore[attr-defined]

    read = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise Chinese answers",
            query_time="2026-01-10T00:00:00+00:00",
            max_units=5,
            context_budget_tokens=80,
        )
    )

    assert read.context.unit_count >= 1
    assert "Relevant memory units:" in read.context.text
    assert "concise Chinese answers" in read.context.text
    assert "2026-01-01T10:00:01+00:00" in read.context.text
    assert read.stats["index_backend"] == "dense_cosine_v1"
    assert read.stats["returned_unit_count"] == read.context.unit_count
    assert read.stats["rendered_unit_ids"]
    assert {item.unit.scope.namespace for item in read.ranked_units} == {"personal"}

    time_filtered = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="concise Chinese answers",
            query_time="2026-01-10T00:00:00+00:00",
            time_range=TimeRange(start="2026-01-02T00:00:00+00:00"),
            max_units=5,
        )
    )
    assert time_filtered.context.unit_count == 0
    assert time_filtered.ranked_units == ()

    stats = _json(handle_manager_get(service, "/manager/api/stats"))
    assert stats["unit_count"] == 3
    assert stats["dialogue_count"] == 2
    assert stats["index_health"] == "synced"

    units = _json(
        handle_manager_get(
            service,
            "/manager/api/memory-units?owner_id=user-1&namespace=personal&limit=10",
        )
    )
    assert units["count"] == 2
    unit_id = units["units"][0]["unit_id"]
    detail = _json(handle_manager_get(service, f"/manager/api/memory-units/{unit_id}"))
    source_chunk = detail["source_chunks"][0]
    assert source_chunk["status"] == "ok"
    assert source_chunk["raw_dialogue_available"] is True
    assert source_chunk["requires_explicit_reveal"] is True
    assert len(source_chunk["dialogue_messages"]) == 2

    preview = _json(
        handle_manager_post(
            service,
            "/manager/api/retrieval-preview",
            {
                "owner_id": "user-1",
                "namespaces": ["personal"],
                "query": "design tradeoffs",
                "query_time": "2026-01-10T00:00:00+00:00",
                "max_units": 5,
                "context_budget_tokens": 80,
            },
        )
    )
    assert preview["context"]["unit_count"] >= 1
    assert preview["stats"]["rendered_unit_ids"]

    reindex = _json(handle_manager_post(service, "/manager/api/reindex", {}))
    assert reindex["indexed_unit_count"] == 3
    assert reindex["index_backend"] == "dense_cosine_v1"

    logs = _json(handle_manager_get(service, "/manager/api/operation-logs?limit=20"))
    operation_types = [item["operation_type"] for item in logs["logs"]]
    assert "capture" in operation_types
    assert "read" in operation_types
    assert "reindex" in operation_types

    service.store.close()  # type: ignore[attr-defined]


def test_session_window_product_flow_flushes_reads_and_surfaces_manager_evidence(
    tmp_path,
) -> None:
    config = config_from_mapping(
        {
            "store": {
                "backend": "sqlite",
                "path": str(tmp_path / "nanomem.db"),
            },
            "index": {
                "backend": "dense",
                "rebuild_on_startup": True,
            },
            "extraction": {
                "max_dialogue_tokens": 512,
            },
            "read": {
                "default_max_units": 6,
            },
        }
    )
    service = service_from_config(config)
    scope = MemoryScope(owner_id="user-1", namespace="personal")

    first = service.capture(
        _capture_request(
            owner_id="user-1",
            namespace="personal",
            session_id="session-alpha",
            occurred_at="2026-02-01T09:00:00+00:00",
            capture_time="2026-02-01T09:00:03+00:00",
            messages=(
                DialogueMessage(
                    role="assistant",
                    content="What should I remember about manager workflows?",
                    timestamp="2026-02-01T09:00:00+00:00",
                    speaker_id="agent",
                ),
                DialogueMessage(
                    role="user",
                    content="I prefer source dialogue links in NanoMem manager.",
                    timestamp="2026-02-01T09:00:01+00:00",
                    speaker_id="user-1",
                ),
            ),
        )
    )
    beta = service.capture(
        _capture_request(
            owner_id="user-1",
            namespace="personal",
            session_id="session-beta",
            occurred_at="2026-02-01T10:00:00+00:00",
            capture_time="2026-02-01T10:00:01+00:00",
            messages=(
                DialogueMessage(
                    role="user",
                    content="I like Python examples in a separate session.",
                    timestamp="2026-02-01T10:00:00+00:00",
                    speaker_id="user-1",
                ),
            ),
        )
    )
    second = service.capture(
        _capture_request(
            owner_id="user-1",
            namespace="personal",
            session_id="session-alpha",
            occurred_at="2026-02-02T09:00:00+00:00",
            capture_time="2026-02-02T09:00:02+00:00",
            messages=(
                DialogueMessage(
                    role="assistant",
                    content="I will remember that you prefer source dialogue links.",
                    timestamp="2026-02-02T09:00:00+00:00",
                    speaker_id="agent",
                ),
                DialogueMessage(
                    role="user",
                    content=(
                        "I usually want compact management screens with date "
                        "filters."
                    ),
                    timestamp="2026-02-02T09:00:01+00:00",
                    speaker_id="user-1",
                ),
            ),
        )
    )

    assert first.unit_count == 0
    assert beta.unit_count == 0
    assert second.unit_count == 0
    assert second.dialogue_id == first.dialogue_id
    assert beta.dialogue_id != first.dialogue_id

    alpha_open = service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-alpha", statuses=("open",))
    )
    assert len(alpha_open) == 1
    alpha_dialogue = service.store.get_dialogue(alpha_open[0].dialogue_id)
    assert alpha_dialogue is not None
    assert len(alpha_dialogue.messages) == 4

    flushed_first_window = service.flush(
        FlushRequest(
            scope=scope,
            session_id="session-alpha",
            flush_time="2026-02-02T09:00:05+00:00",
        )
    )
    assert flushed_first_window.dialogue_count == 1
    assert flushed_first_window.unit_count == 3
    assert {unit.scope for unit in flushed_first_window.units} == {scope}
    assert {unit.dialogue_refs[0].message_range for unit in flushed_first_window.units} == {
        None,
    }

    third = service.capture(
        _capture_request(
            owner_id="user-1",
            namespace="personal",
            session_id="session-alpha",
            occurred_at="2026-02-03T09:00:00+00:00",
            capture_time="2026-02-03T09:00:01+00:00",
            messages=(
                DialogueMessage(
                    role="user",
                    content="I prefer date filters on operations pages.",
                    timestamp="2026-02-03T09:00:00+00:00",
                    speaker_id="user-1",
                ),
            ),
        )
    )
    assert third.unit_count == 0
    assert third.dialogue_id != first.dialogue_id

    flushed_second_window = service.flush(
        FlushRequest(
            scope=scope,
            session_id="session-alpha",
            flush_time="2026-02-03T09:00:05+00:00",
        )
    )
    assert flushed_second_window.dialogue_count == 1
    assert flushed_second_window.unit_count == 1

    beta_open = service.store.query_dialogue_windows(
        DialogueWindowSelector(session_id="session-beta", statuses=("open",))
    )
    assert len(beta_open) == 1
    service.store.close()  # type: ignore[attr-defined]

    service = service_from_config(config)
    assert service.index.document_count() == 4  # type: ignore[attr-defined]

    read = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=None,
            query="source dialogue links compact date filters",
            query_time="2026-02-04T00:00:00+00:00",
            max_units=6,
            context_budget_tokens=200,
        )
    )
    assert read.stats["index_backend"] == "dense_cosine_v1"
    assert read.stats["returned_unit_count"] >= 3
    assert read.stats["skipped_due_to_budget_count"] == 0
    assert "source dialogue links" in read.context.text
    assert "date filters" in read.context.text
    assert "Python examples" not in read.context.text

    stats = _json(handle_manager_get(service, "/manager/api/stats"))
    assert stats["session_count"] == 2
    assert stats["dialogue_window_count"] == 3
    assert stats["open_dialogue_window_count"] == 1
    assert stats["unit_count"] == 4
    assert stats["index_health"] == "synced"

    sessions = _json(handle_manager_get(service, "/manager/api/sessions"))
    assert sessions["count"] == 2
    alpha_summary = next(
        item for item in sessions["sessions"] if item["session_id"] == "session-alpha"
    )
    assert alpha_summary["dialogue_count"] == 2
    assert alpha_summary["window_counts"] == {"extracted": 2}
    assert alpha_summary["produced_unit_count"] == 4

    beta_summary = next(
        item for item in sessions["sessions"] if item["session_id"] == "session-beta"
    )
    assert beta_summary["window_counts"] == {"open": 1}
    assert beta_summary["produced_unit_count"] == 0

    alpha_detail = _json(
        handle_manager_get(service, "/manager/api/sessions/session-alpha")
    )
    assert len(alpha_detail["windows"]) == 2
    assert len(alpha_detail["messages"]) == 5
    assert all(
        message["dialogue_id"]
        in {window["dialogue_id"] for window in alpha_detail["windows"]}
        for message in alpha_detail["messages"]
    )

    first_dialogue_unit = next(
        unit
        for unit in alpha_detail["produced_units"]
        if unit["dialogue_refs"][0]["dialogue_id"] == first.dialogue_id
    )
    unit_id = first_dialogue_unit["unit_id"]
    unit_detail = _json(
        handle_manager_get(service, f"/manager/api/memory-units/{unit_id}")
    )
    source = unit_detail["source_chunks"][0]
    assert source["status"] == "ok"
    assert source["range_label"] == "Full dialogue"
    assert source["dialogue"]["session_id"] == "session-alpha"
    assert source["resolved_range"] == [0, 4]
    assert len(source["dialogue_messages"]) == 4

    preview = _json(
        handle_manager_post(
            service,
            "/manager/api/retrieval-preview",
            {
                "owner_id": "user-1",
                "query": "compact manager date filters",
                "query_time": "2026-02-04T00:00:00+00:00",
                "max_units": 6,
                "context_budget_tokens": 120,
            },
        )
    )
    assert preview["stats"]["index_backend"] == "dense_cosine_v1"
    assert preview["context"]["unit_count"] >= 2
    assert preview["stats"]["rendered_unit_ids"]

    logs = _json(handle_manager_get(service, "/manager/api/operation-logs?limit=30"))
    operation_types = [item["operation_type"] for item in logs["logs"]]
    assert "capture" in operation_types
    assert "flush" in operation_types
    assert "read" in operation_types

    service.store.close()  # type: ignore[attr-defined]


def _capture_request(
    *,
    owner_id: str,
    namespace: str,
    session_id: str | None = None,
    occurred_at: str,
    capture_time: str,
    messages: tuple[DialogueMessage, ...],
) -> CaptureRequest:
    return CaptureRequest(
        scope=MemoryScope(owner_id=owner_id, namespace=namespace),
        dialogue=CaptureDialogue(
            occurred_at=occurred_at,
            messages=messages,
            metadata={"source": "product-flow-test"},
        ),
        capture_time=capture_time,
        session_id=session_id,
    )


def _json(response) -> dict:
    assert response is not None
    assert response.status.value == 200
    return json.loads(response.body.decode("utf-8"))
