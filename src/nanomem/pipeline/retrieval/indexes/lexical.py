from __future__ import annotations

import re

from nanomem.core.contracts import (
    IndexHit,
    IndexSearchRequest,
    MemoryUnit,
)
from nanomem.core.policies import namespace_matches
from nanomem.core.time import timestamp_in_range


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


class LexicalMemoryUnitIndex:
    """Small in-memory lexical index used by the first service slice."""

    name = "lexical_v1"

    def __init__(self) -> None:
        self._documents: dict[str, MemoryUnit] = {}
        self._tokens: dict[str, set[str]] = {}
        self._owner_index: dict[str, set[str]] = {}

    def clear(self) -> None:
        self._documents.clear()
        self._tokens.clear()
        self._owner_index.clear()

    def document_count(self) -> int:
        return len(self._documents)

    def upsert(self, units: tuple[MemoryUnit, ...]) -> None:
        for unit in units:
            existing = self._documents.get(unit.unit_id)
            if existing is not None:
                self._remove_from_scope_index(existing)
            self._documents[unit.unit_id] = unit
            self._tokens[unit.unit_id] = tokenize(unit.text)
            self._add_to_scope_index(unit)

    def search(self, request: IndexSearchRequest) -> tuple[IndexHit, ...]:
        query_tokens = tokenize(request.query)
        if not query_tokens:
            return ()

        hits: list[IndexHit] = []
        for unit_id, unit in self._candidate_units(request):
            timestamp = unit.timestamp or unit.available_at
            if unit.scope.owner_id != request.owner_id:
                continue
            if not namespace_matches(unit.scope.namespace or "", request.namespaces):
                continue
            if not timestamp_in_range(timestamp, request.time_range):
                continue
            document_tokens = self._tokens.get(unit_id, set())
            overlap = query_tokens & document_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(query_tokens), 1)
            hits.append(
                IndexHit(
                    unit_id=unit_id,
                    score=score,
                    retrieval_text=unit.text,
                    score_breakdown={
                        "overlap": sorted(overlap),
                        "query_token_count": len(query_tokens),
                        "document_token_count": len(document_tokens),
                    },
                )
            )

        hits.sort(key=lambda hit: (-hit.score, hit.unit_id))
        if request.limit is not None:
            hits = hits[:request.limit]
        return tuple(hits)

    def delete(self, unit_ids: tuple[str, ...]) -> None:
        for unit_id in unit_ids:
            unit = self._documents.pop(unit_id, None)
            if unit is not None:
                self._remove_from_scope_index(unit)
            self._tokens.pop(unit_id, None)

    def _candidate_units(
        self,
        request: IndexSearchRequest,
    ) -> tuple[tuple[str, MemoryUnit], ...]:
        ids = self._owner_index.get(request.owner_id, set())
        return tuple(
            (unit_id, self._documents[unit_id])
            for unit_id in ids
            if unit_id in self._documents
        )

    def _add_to_scope_index(self, unit: MemoryUnit) -> None:
        self._owner_index.setdefault(unit.scope.owner_id, set()).add(unit.unit_id)

    def _remove_from_scope_index(self, unit: MemoryUnit) -> None:
        ids = self._owner_index.get(unit.scope.owner_id)
        if ids is None:
            return
        ids.discard(unit.unit_id)
        if not ids:
            self._owner_index.pop(unit.scope.owner_id, None)


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_PATTERN.findall(str(text or ""))}
