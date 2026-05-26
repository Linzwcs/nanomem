from __future__ import annotations

import re

from nanomem.core.contracts import PackedContext, RankedMemoryUnit


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]|[^\s]")


class EvidenceContextRenderer:
    name = "evidence_context_v1"

    def render(
        self,
        ranked: tuple[RankedMemoryUnit, ...],
        *,
        budget_tokens: int | None = None,
    ) -> PackedContext:
        if not ranked:
            return PackedContext(text="", token_count=0, unit_count=0)

        lines = ["Relevant memory units:"]
        included = 0
        for item in ranked:
            line = _render_line(item)
            candidate = "\n".join([*lines, line])
            token_count = estimate_tokens(candidate)
            if budget_tokens is not None and token_count > budget_tokens:
                if included == 0:
                    continue
                break
            lines.append(line)
            included += 1

        if included == 0:
            return PackedContext(text="", token_count=0, unit_count=0)
        text = "\n".join(lines)
        return PackedContext(
            text=text,
            token_count=estimate_tokens(text),
            unit_count=included,
        )


def _render_line(item: RankedMemoryUnit) -> str:
    unit = item.unit
    timestamp = unit.timestamp or "unknown"
    labels = [timestamp]
    if unit.scope.namespace:
        labels.append(f"namespace={unit.scope.namespace}")
    return f"- [{', '.join(labels)}] {unit.text}"


def render_line_for_diagnostics(item: RankedMemoryUnit) -> str:
    return _render_line(item)


def estimate_tokens(text: str) -> int:
    return len(TOKEN_PATTERN.findall(str(text or "")))
