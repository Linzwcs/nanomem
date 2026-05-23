from __future__ import annotations

import json

from nanomem.config import config_from_mapping
from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
    TimeRange,
)
from nanomem.factory import service_from_config
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


def _capture_request(
    *,
    owner_id: str,
    namespace: str,
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
    )


def _json(response) -> dict:
    assert response is not None
    assert response.status.value == 200
    return json.loads(response.body.decode("utf-8"))
