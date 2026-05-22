from __future__ import annotations

import pytest

from nanomem.contracts import IndexSearchRequest, TimeRange
from nanomem.index.lancedb import (
    _distance_to_score,
    _normalized_distance_type,
    _search_filter,
)


def test_lancedb_search_filter_scopes_owner_namespace_and_time() -> None:
    expression = _search_filter(
        IndexSearchRequest(
            owner_id="user-1",
            namespaces=("personal", "work"),
            query="preference",
            time_range=TimeRange(
                start="2026-01-01T00:00:00+00:00",
                end="2026-02-01T00:00:00+00:00",
            ),
        )
    )

    assert "(owner_id = 'user-1')" in expression
    assert "(namespace IN ('personal', 'work'))" in expression
    assert "(redacted_at = '')" in expression
    assert "(sort_timestamp >= '2026-01-01T00:00:00+00:00')" in expression
    assert "(sort_timestamp <= '2026-02-01T00:00:00+00:00')" in expression


def test_lancedb_search_filter_escapes_literals() -> None:
    expression = _search_filter(
        IndexSearchRequest(
            owner_id="user's-id",
            namespaces=("owner's-notes",),
            query="preference",
        )
    )

    assert "user''s-id" in expression
    assert "owner''s-notes" in expression


def test_lancedb_distance_type_validation() -> None:
    assert _normalized_distance_type("COSINE") == "cosine"
    with pytest.raises(ValueError, match="Unsupported LanceDB distance_type"):
        _normalized_distance_type("unknown")


def test_lancedb_distance_to_score() -> None:
    assert _distance_to_score(0.25, distance_type="cosine") == 0.75
    assert _distance_to_score(1.0, distance_type="l2") == 0.5
    assert _distance_to_score(-0.7, distance_type="dot") == 0.7
