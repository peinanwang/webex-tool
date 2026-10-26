"""Time helpers.

Webex timestamps are UTC ISO strings like 2026-10-21T14:03:00.123Z, and that's what we store.
People think in local time ("today", "Monday"), so tools take local dates/times,
convert them to UTC strings for queries, and show results in local time.
"""

from datetime import date, datetime, time, timedelta, timezone


def to_webex_utc(dt: datetime) -> str:
    """Datetime → Webex-style UTC string (comparable with stored `created` values)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def now_webex_utc() -> str:
    return to_webex_utc(datetime.now(timezone.utc))


def parse_webex(webex_ts: str) -> datetime:
    """'2026-10-21T14:03:00.123Z' → aware datetime in local time."""
    return datetime.fromisoformat(webex_ts.replace("Z", "+00:00")).astimezone()


def to_local_display(webex_ts: str) -> str:
    """'2026-10-21T14:03:00.123Z' → '2026-10-21 07:03' in this machine's local time."""
    return parse_webex(webex_ts).strftime("%Y-%m-%d %H:%M")


def short_local(webex_ts: str) -> str:
    """'14:05' for today, 'Mon 10/26 14:05' otherwise. Used in chat replies and notifications."""
    dt = parse_webex(webex_ts)
    return dt.strftime("%H:%M") if dt.date() == date.today() else dt.strftime("%a %m/%d %H:%M")


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
    start_dt = _parse_local(start, end_of_day=False) if start else day_start(now.date())
    end_dt = _parse_local(end, end_of_day=True) if end else now
    return start_dt, end_dt


def day_start(d: date) -> datetime:
    return datetime.combine(d, time.min).astimezone()


def period_label(start_dt: datetime, end_dt: datetime) -> str:
    """'2026-10-21' for one day, '2026-10-19_2026-10-21' for a range (used in file names)."""
    first = start_dt.date()
    last = (end_dt - timedelta(microseconds=1)).date()
    return first.isoformat() if first == last else f"{first.isoformat()}_{last.isoformat()}"


def describe_period(start_dt: datetime, end_dt: datetime) -> str:
    """Human label: 'Mon Oct 26, 00:00–14:05' or 'Mon Oct 19 – Wed Oct 21'."""
    start_dt, end_dt = start_dt.astimezone(), end_dt.astimezone()
    last = end_dt - timedelta(seconds=1)
    if start_dt.date() == last.date():
        whole_day = start_dt.time() == time.min and end_dt - start_dt >= timedelta(hours=23, minutes=59)
        day = start_dt.strftime("%a %b %d")
        return day if whole_day else f"{day}, {start_dt:%H:%M}–{end_dt:%H:%M}"
    return f"{start_dt:%a %b %d} – {last:%a %b %d}"
