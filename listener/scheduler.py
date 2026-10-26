"""The end-of-day summary at EOD_TIME (default 23:59), run by APScheduler inside the listener.

APScheduler is a timer library: we register "run end_of_day() every day at 23:59" and it calls the
function from a background thread. If the Mac is asleep or the listener is stopped at that time, the
run is missed, so at startup catch_up() makes any missing days (at most 3 back).

Manual run (e.g. to test without waiting until midnight):

    python -m scripts.run_eod              # today so far
    python -m scripts.run_eod 2026-10-25   # a specific day
"""

from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from shared import config, db, summary
from shared.log import log

MAX_CATCH_UP_DAYS = 3


def _run_today() -> None:
    try:
        summary.end_of_day(date.today())
    except Exception as exc:
        log(f"[error] end-of-day summary failed: {exc}")


def catch_up() -> None:
    """Make end-of-day summaries for days the scheduler missed (listener off, Mac asleep)."""
    yesterday = date.today() - timedelta(days=1)
    last = db.kv_get("eod_last_date")
    if not last:
        db.kv_set("eod_last_date", yesterday.isoformat())  # first run: start from today, no backfill
        return
    day = max(date.fromisoformat(last) + timedelta(days=1), yesterday - timedelta(days=MAX_CATCH_UP_DAYS - 1))
    while day <= yesterday:
        log(f"[eod] catching up on {day}")
        try:
            summary.end_of_day(day)
        except Exception as exc:
            log(f"[error] catch-up summary for {day} failed: {exc}")
            break
        day += timedelta(days=1)


def start() -> BackgroundScheduler | None:
    if not config.EOD_ENABLED:
        return None
    hour, minute = (int(x) for x in config.EOD_TIME.split(":"))
    scheduler = BackgroundScheduler()
    # misfire_grace_time: if the Mac wakes up a little late, still run (up to 1 hour late).
    scheduler.add_job(_run_today, CronTrigger(hour=hour, minute=minute), id="end_of_day",
                      misfire_grace_time=3600, coalesce=True)
    scheduler.add_job(catch_up, id="eod_catch_up")  # once, right away
    scheduler.start()
    log(f"End-of-day summary scheduled daily at {config.EOD_TIME} (outbox: {config.OUTBOX_DIR.name}/)")
    return scheduler
