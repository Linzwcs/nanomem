from __future__ import annotations

from nanomem.contracts import MemoryScope


def scope_matches(candidate: MemoryScope, request: MemoryScope) -> bool:
    return (
        candidate.owner_id == request.owner_id
        and candidate.namespace == request.namespace
    )


def namespace_matches(candidate: str, namespaces: tuple[str, ...] | None) -> bool:
    return namespaces is None or candidate in namespaces
