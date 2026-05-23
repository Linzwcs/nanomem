from __future__ import annotations

import json

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
)
from nanomem.server.manager import handle_manager_get, handle_manager_post
from nanomem.service.core import NanoMemService


def test_manager_console_serves_html() -> None:
    response = handle_manager_get(NanoMemService(), "/admin")

    assert response is not None
    assert response.status.value == 200
    assert response.content_type == "text/html; charset=utf-8"
    assert b"NanoMem Manager" in response.body
    assert b'/manager/assets/styles.css' in response.body
    assert b'/manager/assets/app.js' in response.body

    manager = handle_manager_get(NanoMemService(), "/manager")
    assert manager is not None
    assert manager.status.value == 200
    assert b"NanoMem Manager" in manager.body


def test_manager_console_serves_packaged_assets() -> None:
    service = NanoMemService()

    css = handle_manager_get(service, "/manager/assets/styles.css")
    assert css is not None
    assert css.status.value == 200
    assert css.content_type == "text/css; charset=utf-8"
    assert b".app-shell" in css.body
    assert b".data-table" in css.body

    js = handle_manager_get(service, "/manager/assets/app.js")
    assert js is not None
    assert js.status.value == 200
    assert js.content_type == "text/javascript; charset=utf-8"
    assert b"Memory Units" in js.body
    assert b"Retrieval Preview" in js.body

    missing = handle_manager_get(service, "/manager/assets/missing.js")
    assert missing is not None
    assert missing.status.value == 404


def test_manager_api_lists_stats_units_dialogue_and_logs() -> None:
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

    stats = _json(handle_manager_get(service, "/manager/api/stats"))
    assert stats["unit_count"] == 1
    assert stats["active_unit_count"] == 1
    assert stats["index_backend"] == "dense_cosine_v1"
    assert stats["index_document_count"] == 1
    assert stats["index_health"] == "synced"
    assert stats["index_unit_delta"] == 0

    legacy_stats = _json(handle_manager_get(service, "/admin/api/stats"))
    assert legacy_stats["unit_count"] == 1

    units = _json(
        handle_manager_get(
            service,
            "/manager/api/memory-units?owner_id=user-1&namespace=personal",
        )
    )
    assert units["count"] == 1
    unit_id = units["units"][0]["unit_id"]
    dialogue_id = capture.dialogue_id

    unit = _json(handle_manager_get(service, f"/manager/api/memory-units/{unit_id}"))
    assert unit["unit"]["text"] == "I prefer concise Chinese answers."
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

    dialogue = _json(handle_manager_get(service, f"/manager/api/dialogues/{dialogue_id}"))
    assert dialogue["dialogue"]["dialogue_id"] == dialogue_id
    assert len(dialogue["produced_units"]) == 1

    logs = _json(handle_manager_get(service, "/manager/api/operation-logs?limit=10"))
    assert logs["count"] == 1
    assert logs["logs"][0]["operation_type"] == "capture"


def test_manager_api_filters_memory_units_by_date_and_order() -> None:
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
        handle_manager_get(
            service,
            "/manager/api/memory-units"
            "?owner_id=user-1"
            "&start=2026-01-02T00:00:00%2B00:00"
            "&order=oldest_first",
        )
    )

    assert filtered["selector"]["order"] == "oldest_first"
    assert filtered["selector"]["time_range"]["start"] == "2026-01-02T00:00:00+00:00"
    assert filtered["count"] == 1
    assert filtered["units"][0]["text"] == "I prefer fact-level memory units."


def test_manager_api_paginates_memory_units_and_reports_totals() -> None:
    service = NanoMemService()
    for index, text in (
        (1, "I prefer concise Chinese answers."),
        (2, "I prefer fact-level memory units."),
        (3, "I prefer local-first memory storage."),
    ):
        service.capture(
            CaptureRequest(
                scope=MemoryScope(owner_id="user-1", namespace="personal"),
                dialogue=CaptureDialogue(
                    occurred_at=f"2026-01-0{index}T00:00:00+00:00",
                    messages=(
                        DialogueMessage(
                            role="user",
                            content=text,
                            timestamp=f"2026-01-0{index}T00:00:00+00:00",
                        ),
                    ),
                ),
                capture_time=f"2026-01-0{index}T00:00:01+00:00",
            )
        )

    first_page = _json(
        handle_manager_get(
            service,
            "/manager/api/memory-units?owner_id=user-1&limit=2&page=1&text=prefer",
        )
    )
    second_page = _json(
        handle_manager_get(
            service,
            "/manager/api/memory-units?owner_id=user-1&limit=2&page=2&text=prefer",
        )
    )

    assert first_page["count"] == 2
    assert first_page["total_count"] == 3
    assert first_page["offset"] == 0
    assert first_page["has_more"] is True
    assert second_page["count"] == 1
    assert second_page["total_count"] == 3
    assert second_page["offset"] == 2
    assert second_page["has_more"] is False


def test_manager_api_retrieval_preview_and_reindex() -> None:
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
        handle_manager_post(
            service,
            "/manager/api/retrieval-preview",
            {
                "owner_id": "user-1",
                "namespaces": None,
                "query": "concise Chinese answers",
            },
        )
    )
    assert preview["context"]["unit_count"] == 1
    assert preview["stats"]["index_backend"] == "dense_cosine_v1"
    assert preview["stats"]["returned_unit_count"] == 1
    assert preview["stats"]["skipped_due_to_budget_count"] == 0
    assert len(preview["stats"]["rendered_unit_ids"]) == 1
    assert len(preview["stats"]["ranked_token_estimates"]) == 1

    reindex = _json(handle_manager_post(service, "/manager/api/reindex", {}))
    assert reindex["indexed_unit_count"] == 1
    assert reindex["index_backend"] == "dense_cosine_v1"

    stats = _json(handle_manager_get(service, "/manager/api/stats"))
    assert stats["last_reindex_at"] is not None

    logs = _json(handle_manager_get(service, "/manager/api/operation-logs?limit=10"))
    assert any(log["operation_type"] == "reindex" for log in logs["logs"])


def test_manager_stats_reports_stale_index_after_index_clear() -> None:
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
    service.index.clear()

    stats = _json(handle_manager_get(service, "/manager/api/stats"))

    assert stats["active_unit_count"] == 1
    assert stats["index_document_count"] == 0
    assert stats["index_health"] == "stale"
    assert stats["index_unit_delta"] == 1


def _json(response) -> dict:
    assert response is not None
    assert response.status.value == 200
    return json.loads(response.body.decode("utf-8"))
