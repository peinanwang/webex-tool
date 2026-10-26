"""Time helpers.

Webex timestamps are UTC ISO strings like 2026-10-21T14:03:00.123Z, and that's what we store.
People think in local time ("today", "Monday"), so the MCP tools take local dates/times,
convert them to UTC strings for queries, and show results in local time.
"""

from datetime import date, datetime, time, timedelta, timezone


def to_webex_utc(dt: datetime) -> str:
    """Datetime → Webex-style UTC string (comparable with stored `created` values)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def now_webex_utc() -> str:
    return to_webex_utc(datetime.now(timezone.utc))


def to_local_display(webex_ts: str) -> str:
    """'2026-10-21T14:03:00.123Z' → '2026-10-21 07:03' in this machine's local time."""
    dt = datetime.fromisoformat(webex_ts.replace("Z", "+00:00"))
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def _parse_local(value: str, end_of_day: bool) -> datetime:
    """'2026-10-21' or '2026-10-21T09:00' (local) → aware datetime.

    A date alone means the start of that day, or (for an end bound) the start of the next day.
    """
    if len(value) == 10:
        d = date.fromisoformat(value)
        if end_of_day:
            d += timedelta(days=1)
        return datetime.combine(d, time.min).astimezone()
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.astimezone()


def period_bounds(start: str | None, end: str | None) -> tuple[datetime, datetime]:
    """Local start/end (end exclusive). Defaults: today from midnight until now."""
    now = datetime.now().astimezone()
    start_dt = _parse_local(start, end_of_day=False) if start else datetime.combine(now.date(), time.min).astimezone()
    end_dt = _parse_local(end, end_of_day=True) if end else now
    return start_dt, end_dt


def period_label(start_dt: datetime, end_dt: datetime) -> str:
    """'2026-10-21' for one day, '2026-10-19_2026-10-21' for a range (used in digest file names)."""
    first = start_dt.date()
    last = (end_dt - timedelta(microseconds=1)).date()
    return first.isoformat() if first == last else f"{first.isoformat()}_{last.isoformat()}"
