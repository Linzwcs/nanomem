from __future__ import annotations

import json

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
)
from nanomem.server.admin import handle_admin_get, handle_admin_post
from nanomem.service.core import NanoMemService


def test_admin_console_serves_html() -> None:
    response = handle_admin_get(NanoMemService(), "/admin")

    assert response is not None
    assert response.status.value == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert b"NanoMem Manager" in response.body
    assert b'/manager/assets/styles.css' in response.body
    assert b'/manager/assets/app.js' in response.body

    manager = handle_admin_get(NanoMemService(), "/manager")
    assert manager is not None
    assert manager.status.value == 200
    assert b"NanoMem Manager" in manager.body


def test_admin_console_serves_packaged_assets() -> None:
    service = NanoMemService()

    css = handle_admin_get(service, "/manager/assets/styles.css")
    assert css is not None
    assert css.status.value == 200
    assert css.content_type == "text/css; charset=utf-8"
    assert b".detail-page" in css.body

    js = handle_admin_get(service, "/manager/assets/app.js")
    assert js is not None
    assert js.status.value == 200
    assert js.content_type == "text/javascript; charset=utf-8"
    assert b"renderMemoryUnitDetail" in js.body

    missing = handle_admin_get(service, "/manager/assets/missing.js")
    assert missing is not None
    assert missing.status.value == 404


def test_admin_api_lists_stats_units_dialogue_and_logs() -> None:
    service = NanoMemService()
    capture = service.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            dialogue=CaptureDialogue(
                occurred_at="2026-01-01T00:00:00+00:00",
                messages=(
                    DialogueMessage(
                        role="assistant",
                        content="What should I remember?",
                        timestamp="2026-01-01T00:00:00+00:00",
                    ),
                    DialogueMessage(
                        role="user",
                        content="I prefer concise Chinese answers.",
                        timestamp="2026-01-01T00:00:01+00:00",
                    ),
                ),
            ),
            capture_time="2026-01-01T00:00:01+00:00",
        )
    )

    stats = _json(handle_admin_get(service, "/admin/api/stats"))
    assert stats["unit_count"] == 1
    assert stats["index_backend"] == "dense_cosine_v1"

    units = _json(
        handle_admin_get(
            service,
            "/admin/api/memory-units?owner_id=user-1&namespace=personal",
        )
    )
    assert units["count"] == 1
    unit_id = units["units"][0]["unit_id"]
    dialogue_id = capture.dialogue_id

    unit = _json(handle_admin_get(service, f"/admin/api/memory-units/{unit_id}"))
    assert unit["unit"]["text"] == "The user said they prefer concise Chinese answers."
    assert unit["source_chunks"][0]["ref"]["message_range"] == [1, 2]
    assert unit["source_chunks"][0]["status"] == "ok"
    assert unit["source_chunks"][0]["range_label"] == "messages [1, 2)"
    assert unit["source_chunks"][0]["resolved_message_count"] == 1
    assert unit["source_chunks"][0]["messages"][0]["content"] == (
        "I prefer concise Chinese answers."
    )
    assert len(unit["source_chunks"][0]["dialogue_messages"]) == 2
    assert unit["source_chunks"][0]["dialogue_messages"][0]["in_ref_range"] is False
    assert unit["source_chunks"][0]["dialogue_messages"][1]["in_ref_range"] is True

    dialogue = _json(handle_admin_get(service, f"/admin/api/dialogues/{dialogue_id}"))
    assert dialogue["dialogue"]["dialogue_id"] == dialogue_id
    assert len(dialogue["produced_units"]) == 1

    logs = _json(handle_admin_get(service, "/admin/api/operation-logs?limit=10"))
    assert logs["count"] == 1
    assert logs["logs"][0]["operation_type"] == "capture"


def test_admin_api_filters_memory_units_by_date_and_order() -> None:
    service = NanoMemService()
    for day, text in (
        ("2026-01-01", "I prefer concise Chinese answers."),
        ("2026-01-02", "I prefer fact-level memory units."),
    ):
        service.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                dialogue=CaptureDialogue(
                    occurred_at=f"{day}T00:00:00+00:00",
                    messages=(
                        DialogueMessage(
                            role="user",
                            content=text,
                            timestamp=f"{day}T00:00:00+00:00",
                        ),
                    ),
                ),
                capture_time=f"{day}T00:00:01+00:00",
            )
        )

    filtered = _json(
        handle_admin_get(
            service,
            "/admin/api/memory-units"
            "?owner_id=user-1"
            "&start=2026-01-02T00:00:00%2B00:00"
            "&order=oldest_first",
        )
    )

    assert filtered["selector"]["order"] == "oldest_first"
    assert filtered["selector"]["time_range"]["start"] == "2026-01-02T00:00:00+00:00"
    assert filtered["count"] == 1
    assert filtered["units"][0]["text"] == (
        "The user said they prefer fact-level memory units."
    )


def test_admin_api_retrieval_preview_and_reindex() -> None:
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

    preview = _json(
        handle_admin_post(
            service,
            "/admin/api/retrieval-preview",
            {
                "owner_id": "user-1",
                "namespaces": None,
                "query": "concise Chinese answers",
            },
        )
    )
    assert preview["context"]["unit_count"] == 1
    assert preview["stats"]["index_backend"] == "dense_cosine_v1"

    reindex = _json(handle_admin_post(service, "/admin/api/reindex", {}))
    assert reindex["indexed_unit_count"] == 1
    assert reindex["index_backend"] == "dense_cosine_v1"


def _json(response) -> dict:
    assert response is not None
    assert response.status.value == 200
    return json.loads(response.body.decode("utf-8"))
