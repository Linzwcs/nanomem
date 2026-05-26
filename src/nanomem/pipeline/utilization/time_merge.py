"""Time-bucket merging renderer.

Implements the paper's ``Time+Merge`` utilization policy. The key design
choice is that the **time format string itself is the merge bucket key**.
Coarser format → more facts collapse into one block:

::

    time_format="%Y-%m-%d %H:%M"   minute granularity → almost no merge
    time_format="%Y-%m-%d"          daily buckets        → typical setting
    time_format="%Y-%m"             monthly              → aggressive merge
    time_format="%Y"                yearly                → extreme merge

Units within the same bucket and namespace are joined with a separator
(default ``" | "``). Units whose timestamp cannot be parsed fall into
an ``unknown`` bucket and are not merged with anything.

Layout (default ``%Y-%m-%d``)::

    Relevant memory units:
    - [2026-05-19, namespace=personal] prefers concise Chinese answers | dislikes verbose replies
    - [2026-05-20, namespace=personal] is working on a paper about agent memory
    - [unknown, namespace=work] (one unparseable item)

Implements :class:`~nanomem.pipeline.utilization.base.Renderer`.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import OrderedDict

from nanomem.core.contracts import PackedContext, RankedMemoryUnit
from nanomem.pipeline.utilization.evidence_context import estimate_tokens


_FALLBACK_FORMATS: tuple[str, ...] = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%I:%M %p on %d %B, %Y",
    "%I:%M %p on %d %b, %Y",
)


def parse_timestamp(timestamp: str | None) -> dt.datetime | None:
    """Best-effort timestamp parse.

    Returns ``None`` when the input is empty, ``"unknown"``, or doesn't
    match any known format. ISO 8601 (the contracts default) is tried
    first via :meth:`datetime.fromisoformat`; older or stylized formats
    fall back to a small list of ``strptime`` patterns.
    """
    raw = str(timestamp or "").strip()
    if not raw or raw.lower() == "unknown":
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    normalized = re.sub(
        r"\b(am|pm)\b",
        lambda m: m.group(1).upper(),
        raw,
        flags=re.IGNORECASE,
    )
    for fmt in _FALLBACK_FORMATS:
        try:
            return dt.datetime.strptime(normalized, fmt)
        except (ValueError, TypeError):
            continue
    return None


def bucket_key(timestamp: str | None, time_format: str) -> str:
    """Return the merge bucket key for a timestamp under a chosen format.

    Unparseable timestamps return ``"unknown"`` so they land in a
    well-known bucket but are not silently grouped with parseable ones.
    """
    parsed = parse_timestamp(timestamp)
    if parsed is None:
        return "unknown"
    return parsed.strftime(time_format)


class TimeMergedRenderer:
    """Render ranked units grouped by configurable time-format buckets.

    Parameters
    ----------
    time_format:
        ``strftime`` format string. Becomes the merge bucket key.
        Larger granularity = more merging.
    separator:
        String used to join multiple units within the same bucket.
    """

    name = "time_merged_v1"

    def __init__(
        self,
        *,
        time_format: str = "%Y-%m-%d",
        separator: str = " | ",
    ) -> None:
        self.time_format = time_format
        self.separator = separator

    def render(
        self,
        ranked: tuple[RankedMemoryUnit, ...],
        *,
        budget_tokens: int | None = None,
    ) -> PackedContext:
        if not ranked:
            return PackedContext(text="", token_count=0, unit_count=0)

        # Group by (bucket, namespace), preserving the rank-order of first
        # occurrence so the most relevant bucket appears first.
        grouped: OrderedDict[tuple[str, str | None], list[RankedMemoryUnit]] = OrderedDict()
        for item in ranked:
            key = (
                bucket_key(item.unit.timestamp, self.time_format),
                item.unit.scope.namespace,
            )
            grouped.setdefault(key, []).append(item)

        # Group-atomic budget packing: a bucket either fits whole or is
        # skipped. Never render half a group.
        lines = ["Relevant memory units:"]
        unit_count = 0
        for (bucket, namespace), items in grouped.items():
            line = _format_group(
                bucket=bucket,
                namespace=namespace,
                items=items,
                separator=self.separator,
            )
            candidate = "\n".join([*lines, line])
            tokens = estimate_tokens(candidate)
            if budget_tokens is not None and tokens > budget_tokens:
                if unit_count == 0:
                    # First group too big; try smaller ones next.
                    continue
                break
            lines.append(line)
            unit_count += len(items)

        if unit_count == 0:
            return PackedContext(text="", token_count=0, unit_count=0)
        text = "\n".join(lines)
        return PackedContext(
            text=text,
            token_count=estimate_tokens(text),
            unit_count=unit_count,
        )


def _format_group(
    *,
    bucket: str,
    namespace: str | None,
    items: list[RankedMemoryUnit],
    separator: str,
) -> str:
    labels = [bucket]
    if namespace:
        labels.append(f"namespace={namespace}")
    label = "[" + ", ".join(labels) + "]"
    body = separator.join(item.unit.text for item in items)
    return f"- {label} {body}"


__all__ = [
    "TimeMergedRenderer",
    "bucket_key",
    "parse_timestamp",
]
