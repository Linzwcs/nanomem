from __future__ import annotations

from nanomem.core.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryUnit,
    MemoryScope,
    OperationLogSelector,
    ReadRequest,
)
from nanomem.service.core import NanoMemService


def test_capture_resolves_default_namespace_and_read_has_no_default_time_filter() -> None:
    service = NanoMemService()
    capture = service.capture(
        CaptureRequest(
            scope=MemoryScope(owner_id="user-1"),
            dialogue=CaptureDialogue(
                occurred_at="2020-01-01T00:00:00+00:00",
                messages=(
                    DialogueMessage(
                        role="user",
                        speaker_id="user-1",
                        content="I prefer concise Chinese answers.",
                        timestamp="2020-01-01T00:00:00+00:00",
                    ),
                ),
            ),
            capture_time="2020-01-01T00:00:01+00:00",
        )
    )

    assert capture.unit_count == 1
    assert capture.units[0].scope == MemoryScope(
        owner_id="user-1",
        namespace="personal",
    )

    read = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=None,
            query="concise Chinese answers",
            query_time="2026-01-01T00:00:00+00:00",
        )
    )

    assert len(read.ranked_units) == 1
    assert read.stats["recency_policy"] == "balanced"
    assert "concise Chinese answers" in read.context.text


def test_read_namespace_filter_excludes_other_namespaces() -> None:
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

    read = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("work",),
            query="concise Chinese answers",
            query_time="2026-01-02T00:00:00+00:00",
        )
    )

    assert read.ranked_units == ()
    assert read.context.unit_count == 0


def test_repeated_reads_do_not_collide_operation_log_ids() -> None:
    service = NanoMemService()
    request = ReadRequest(
        owner_id="user-1",
        namespaces=None,
        query="same query",
        query_time="2026-01-02T00:00:00+00:00",
    )

    service.read(request)
    service.read(request)

    logs = service.store.list_operation_logs(OperationLogSelector(limit=None))
    assert len(logs) == 2
    assert logs[0].log_id != logs[1].log_id


def test_read_reports_render_budget_diagnostics() -> None:
    service = NanoMemService()
    units = (
        MemoryUnit(
            unit_id="unit-1",
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            text="alpha",
            memory_type="preference",
            timestamp="2026",
            available_at="2026",
        ),
        MemoryUnit(
            unit_id="unit-2",
            scope=MemoryScope(owner_id="user-1", namespace="personal"),
            text="beta",
            memory_type="preference",
            timestamp="2026",
            available_at="2026",
        ),
    )
    service.store.append_units(units)
    service.index.upsert(units)

    read = service.read(
        ReadRequest(
            owner_id="user-1",
            namespaces=("personal",),
            query="alpha beta",
            query_time="2026-01-02T00:00:00+00:00",
            max_units=2,
            context_budget_tokens=18,
        )
    )

    assert read.stats["ranked_count"] == 2
    assert read.stats["returned_unit_count"] == 1
    assert read.stats["skipped_due_to_budget_count"] == 1
    assert len(read.stats["rendered_unit_ids"]) == 1
    assert len(read.stats["skipped_unit_ids"]) == 1
    assert len(read.stats["ranked_token_estimates"]) == 2
