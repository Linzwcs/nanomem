from __future__ import annotations

import argparse
from pathlib import Path

from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    MemoryUnitSelector,
    ReadRequest,
    TimeRange,
)
from nanomem.service.core import NanoMemService
from nanomem.store.sqlite import SQLiteMemoryUnitStore


DEFAULT_DB = ".nanomem/simulations/memory-flow/memory_flow.db"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a complete local NanoMem test database."
    )
    parser.add_argument("--path", default=DEFAULT_DB)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    if path.exists() and not args.force:
        raise SystemExit(f"{path} already exists; pass --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    service = NanoMemService(store=SQLiteMemoryUnitStore(path))
    for request in capture_requests():
        service.capture(request)

    service.reindex()
    for request in read_requests():
        service.read(request)

    units = service.store.query_units(MemoryUnitSelector(limit=None))
    missing_refs = missing_dialogue_refs(service, units)
    if missing_refs:
        raise SystemExit(
            "Generated database has unresolved DialogueRefs: "
            + ", ".join(missing_refs)
        )

    print(f"database={path}")
    print(f"unit_count={len(units)}")
    print(f"dialogue_count={len({ref.dialogue_id for unit in units for ref in unit.dialogue_refs})}")
    print("missing_dialogue_refs=0")
    print("ready_for_manager=true")


def capture_requests() -> tuple[CaptureRequest, ...]:
    return (
        capture(
            namespace="personal",
            occurred_at="2026-05-01T09:00:00+00:00",
            capture_time="2026-05-01T09:00:05+00:00",
            scenario="preference",
            messages=(
                message(
                    "user",
                    "We are designing NanoMem as a personal memory layer for agents.",
                    "2026-05-01T09:00:00+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "Which answer style should be treated as durable personal memory?",
                    "2026-05-01T09:00:20+00:00",
                    speaker_id="nanomem-agent",
                ),
                message(
                    "user",
                    "I prefer concise Chinese answers. Please remember that I usually want architecture first, then code.",
                    "2026-05-01T09:00:42+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "Noted. The durable memory should keep the answer-style preference separate from project documents.",
                    "2026-05-01T09:01:05+00:00",
                    speaker_id="nanomem-agent",
                ),
            ),
        ),
        capture(
            namespace="work",
            occurred_at="2026-05-02T09:00:00+00:00",
            capture_time="2026-05-02T09:00:05+00:00",
            scenario="namespace_design_preference",
            messages=(
                message(
                    "user",
                    "For NanoMem, the project has local docs and code, while personal memory should stay compact.",
                    "2026-05-02T09:00:00+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "Should the system store coarse summaries or small facts for this owner?",
                    "2026-05-02T09:00:21+00:00",
                    speaker_id="nanomem-agent",
                ),
                message(
                    "user",
                    "I prefer fact-level memory units when discussing NanoMem design.",
                    "2026-05-02T09:00:45+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "That keeps retrieval simple and leaves files to the agent workspace.",
                    "2026-05-02T09:01:08+00:00",
                    speaker_id="nanomem-agent",
                ),
            ),
        ),
        capture(
            namespace="personal",
            occurred_at="2026-05-03T09:00:00+00:00",
            capture_time="2026-05-03T09:00:05+00:00",
            scenario="workspace_skip_and_tool_log",
            messages=(
                message(
                    "user",
                    "The README should mention local setup commands.",
                    "2026-05-03T09:00:00+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "tool",
                    "pytest output: 20 passed, 1 skipped.",
                    "2026-05-03T09:00:01+00:00",
                    speaker_id="pytest",
                ),
                message(
                    "assistant",
                    "The README and raw test output should remain workspace evidence rather than personal memory.",
                    "2026-05-03T09:00:02+00:00",
                    speaker_id="nanomem-agent",
                ),
                message(
                    "user",
                    "Please remember that I do not want raw tool logs stored as long-term personal memory.",
                    "2026-05-03T09:00:30+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "Understood. Tool output can remain available through operation logs, not durable personal facts.",
                    "2026-05-03T09:00:54+00:00",
                    speaker_id="nanomem-agent",
                ),
            ),
        ),
        capture(
            namespace="personal",
            occurred_at="2026-05-04T09:00:00+00:00",
            capture_time="2026-05-04T09:00:05+00:00",
            scenario="correction",
            messages=(
                message(
                    "assistant",
                    "The previous plan was detailed and included a long implementation checklist.",
                    "2026-05-04T09:00:00+00:00",
                    speaker_id="nanomem-agent",
                ),
                message(
                    "user",
                    "Correction: I now prefer concise plans unless I explicitly ask for detail.",
                    "2026-05-04T09:00:24+00:00",
                    speaker_id="user-sim",
                    metadata={"memory_type": "correction"},
                ),
                message(
                    "assistant",
                    "Acknowledged. Future planning output should be shorter unless detail is requested.",
                    "2026-05-04T09:00:49+00:00",
                    speaker_id="nanomem-agent",
                ),
            ),
        ),
        capture(
            namespace="manual",
            occurred_at="2026-05-05T09:00:00+00:00",
            capture_time="2026-05-05T09:00:05+00:00",
            scenario="curated_memory",
            messages=(
                message(
                    "user",
                    "The manual namespace is for curated memories created during admin review.",
                    "2026-05-05T09:00:00+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "What should the fixture prove about curated memories?",
                    "2026-05-05T09:00:18+00:00",
                    speaker_id="nanomem-agent",
                ),
                message(
                    "user",
                    "Please remember that manually curated NanoMem memories must remain retrievable after index rebuild.",
                    "2026-05-05T09:00:44+00:00",
                    speaker_id="user-sim",
                    metadata={"fixture": "curated_memory"},
                ),
                message(
                    "assistant",
                    "That fixture can validate that rebuild uses the authoritative store.",
                    "2026-05-05T09:01:02+00:00",
                    speaker_id="nanomem-agent",
                ),
            ),
        ),
        capture(
            namespace="events",
            occurred_at="2026-05-06T09:00:00+00:00",
            capture_time="2026-05-06T09:00:05+00:00",
            scenario="user_event",
            messages=(
                message(
                    "assistant",
                    "Which dated event should be retained as personal history?",
                    "2026-05-06T09:00:00+00:00",
                    speaker_id="nanomem-agent",
                ),
                message(
                    "user",
                    "Please remember that I joined the NanoMem design review on May 6, 2026.",
                    "2026-05-06T09:00:28+00:00",
                    speaker_id="user-sim",
                    metadata={"memory_type": "event"},
                ),
                message(
                    "assistant",
                    "The event belongs in the events namespace and can be retrieved by date or topic.",
                    "2026-05-06T09:00:48+00:00",
                    speaker_id="nanomem-agent",
                ),
            ),
        ),
        capture(
            namespace="agent",
            occurred_at="2026-05-07T09:00:00+00:00",
            capture_time="2026-05-07T09:00:05+00:00",
            scenario="agent_behavior",
            messages=(
                message(
                    "user",
                    "Can you confirm the response style for later sessions?",
                    "2026-05-07T09:00:00+00:00",
                    speaker_id="user-sim",
                ),
                message(
                    "assistant",
                    "I will remember that you prefer concise Chinese answers in future sessions.",
                    "2026-05-07T09:00:19+00:00",
                    speaker_id="nanomem-agent",
                    metadata={"memory_type": "agent_behavior"},
                ),
                message(
                    "user",
                    "Good, use that style when the next session starts.",
                    "2026-05-07T09:00:41+00:00",
                    speaker_id="user-sim",
                ),
            ),
        ),
    )


def capture(
    *,
    namespace: str,
    occurred_at: str,
    capture_time: str,
    scenario: str,
    messages: tuple[DialogueMessage, ...],
) -> CaptureRequest:
    return CaptureRequest(
        scope=MemoryScope(owner_id="user-sim", namespace=namespace),
        dialogue=CaptureDialogue(
            occurred_at=occurred_at,
            messages=messages,
            metadata={"scenario": scenario},
        ),
        capture_time=capture_time,
    )


def message(
    role: str,
    content: str,
    timestamp: str,
    *,
    speaker_id: str,
    metadata: dict[str, object] | None = None,
) -> DialogueMessage:
    return DialogueMessage(
        role=role,
        content=content,
        timestamp=timestamp,
        speaker_id=speaker_id,
        metadata=dict(metadata or {}),
    )


def read_requests() -> tuple[ReadRequest, ...]:
    return (
        read("answer style architecture first concise plans"),
        read("NanoMem fact-level memory units", namespaces=("work",)),
        read("curated memories retrievable index rebuild", namespaces=("manual",)),
        read("joined design review event", namespaces=("events",)),
        read("agent promised concise Chinese answers", namespaces=("agent",)),
        read(
            "concise plans architecture",
            time_range=TimeRange(start="2026-05-04T00:00:00+00:00"),
        ),
    )


def read(
    query: str,
    *,
    namespaces: tuple[str, ...] | None = None,
    time_range: TimeRange | None = None,
) -> ReadRequest:
    return ReadRequest(
        owner_id="user-sim",
        namespaces=namespaces,
        query=query,
        query_time="2026-05-20T00:00:00+00:00",
        time_range=time_range,
        max_units=5,
    )


def missing_dialogue_refs(service: NanoMemService, units: object) -> list[str]:
    missing: list[str] = []
    for unit in units:
        for ref in unit.dialogue_refs:
            dialogue = service.store.get_dialogue(ref.dialogue_id)
            if dialogue is None:
                missing.append(f"{unit.unit_id}:{ref.dialogue_id}")
                continue
            if ref.message_range is None:
                continue
            start, end = ref.message_range
            if start < 0 or end > len(dialogue.messages) or start >= end:
                missing.append(
                    f"{unit.unit_id}:{ref.dialogue_id}[{start},{end})"
                )
    return missing


if __name__ == "__main__":
    main()
