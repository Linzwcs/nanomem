"""Scope and namespace matching helpers.

These predicates are used by the index backends to apply the scope
filter from a :class:`~nanomem.contracts.requests.IndexSearchRequest`
before retrieval scoring.
"""

from __future__ import annotations

from nanomem.core.contracts import MemoryScope


def scope_matches(candidate: MemoryScope, request: MemoryScope) -> bool:
    """Return ``True`` when ``candidate`` exactly matches ``request`` scope."""
    return (
        candidate.owner_id == request.owner_id
        and candidate.namespace == request.namespace
    )


def namespace_matches(
    candidate: str,
    namespaces: tuple[str, ...] | None,
) -> bool:
    """Return ``True`` when ``namespaces`` is unset or contains ``candidate``."""
    return namespaces is None or candidate in namespaces


__all__ = [
    "namespace_matches",
    "scope_matches",
]
