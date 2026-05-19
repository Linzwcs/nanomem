from __future__ import annotations

from datetime import datetime, timezone

from nanomem.contracts import TimeRange


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def timestamp_in_range(value: str | None, time_range: TimeRange | None) -> bool:
    if time_range is None:
        return True
    parsed = parse_timestamp(value)
    if parsed is None:
        return False
    start = parse_timestamp(time_range.start)
    end = parse_timestamp(time_range.end)
    if start is not None and parsed < start:
        return False
    if end is not None and parsed > end:
        return False
    return True


def recency_score(value: str | None, *, query_time: str | None) -> float:
    parsed = parse_timestamp(value)
    query_at = parse_timestamp(query_time) or datetime.now(timezone.utc)
    if parsed is None:
        return 0.0
    age_days = max((query_at - parsed).total_seconds() / 86400.0, 0.0)
    return 1.0 / (1.0 + age_days / 30.0)
