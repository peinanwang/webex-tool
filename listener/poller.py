"""Polling mode: ask Webex for new messages every POLL_INTERVAL seconds (no ngrok needed).

Each room has a cursor in the kv table (`poll_cursor:<roomId>`) holding the `created` time of
the newest message we've handled there. Cursors persist, so after a restart we catch up on
whatever arrived while the listener was down.

On the very first run we record `poll_started_at` = now and only take messages after that,
so old history isn't imported.
"""

import asyncio

from listener.pipeline import process_message
from shared.log import log
from shared import config
from shared import webex_client as wx
from shared.db import kv_get, kv_set
from shared.timeutil import now_webex_utc

# Shown in the UI's top bar ("polling · 1s ago"): when the last pass finished without an error.
last_ok_at: str | None = None
last_error: str | None = None


def poll_once() -> int:
    """One pass over recently active rooms. Returns how many new messages were found."""
    started_at = kv_get("poll_started_at")
    if not started_at:
        started_at = now_webex_utc()
        kv_set("poll_started_at", started_at)

    found = 0
    for room in wx.list_rooms(max_items=50):
        cursor = kv_get(f"poll_cursor:{room['id']}") or started_at
        # Rooms come sorted by last activity, so once one is older than its cursor we could stop,
        # but cursors differ per room; checking each is cheap and simpler to reason about.
        if room.get("lastActivity", "") <= cursor:
            continue

        newest_first = wx.list_messages(room["id"], max_items=50)
        new = [m for m in newest_first if m["created"] > cursor]
        for msg in reversed(new):  # oldest first, so the log reads in order
            try:
                process_message(msg["id"], msg)
            except Exception as exc:
                log(f"[error] message {msg['id']}: {exc}")
        if new:
            kv_set(f"poll_cursor:{room['id']}", new[0]["created"])
            found += len(new)
    return found


async def poll_forever() -> None:
    """Background loop started by the listener's lifespan in polling mode."""
    global last_ok_at, last_error
    while True:
        try:
            # poll_once makes blocking HTTP calls; run it in a thread so the web server stays responsive.
            await asyncio.to_thread(poll_once)
            last_ok_at, last_error = now_webex_utc(), None
        except Exception as exc:
            last_error = str(exc)
            log(f"[error] poll failed: {exc}")  # keep looping; next pass may work
        await asyncio.sleep(config.POLL_INTERVAL)
