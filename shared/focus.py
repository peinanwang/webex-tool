"""Focus mode: the on/off switch.

On  → high messages notify A.
Off → nothing notifies, but every message is still triaged and stored (summaries need it).

State lives in kv: `focus_mode` ('on' / 'off') and `focus_session_id` (the running session).
Each on → off stretch is a row in `focus_sessions`, so Phase 7 can summarize exactly that window.
Focus starts off on a fresh install. Turning it on (or off) twice is harmless.

Quick test before the chat exists:

    python -m shared.focus on | off | status
"""

import sys

from shared import db
from shared.timeutil import now_webex_utc, to_local_display


def is_on() -> bool:
    return db.kv_get("focus_mode") == "on"


def status() -> dict:
    """{'on', 'session_id', 'since', 'counts'}. counts = messages per category so far this session."""
    if not is_on():
        return {"on": False, "session_id": None, "since": None, "counts": None}
    session = db.get_focus_session(int(db.kv_get("focus_session_id")))
    return {
        "on": True,
        "session_id": session["id"],
        "since": session["started_at"],
        "counts": db.count_by_category(session["started_at"], now_webex_utc()),
    }


def turn_on() -> dict:
    """Start a session. Returns status() plus 'changed' (False if it was already on)."""
    if is_on():
        return {**status(), "changed": False}
    session_id = db.start_focus_session(now_webex_utc())
    db.kv_set("focus_session_id", str(session_id))
    db.kv_set("focus_mode", "on")
    return {**status(), "changed": True}


def turn_off() -> dict:
    """End the running session. Returns the closed session row plus 'changed'.

    Phase 7 hooks the "what you missed" summary in here.
    """
    if not is_on():
        return {"changed": False, "session": None}
    session_id = int(db.kv_get("focus_session_id"))
    db.end_focus_session(session_id, now_webex_utc())
    db.kv_set("focus_mode", "off")
    db.kv_set("focus_session_id", "")
    return {"changed": True, "session": db.get_focus_session(session_id)}


def _print_status() -> None:
    s = status()
    if not s["on"]:
        print("Focus is OFF (nothing notifies; messages are still stored).")
        return
    c = s["counts"]
    print(f"Focus is ON since {to_local_display(s['since'])} (session #{s['session_id']}): "
          f"{c['high']} high, {c['regular']} regular so far.")


if __name__ == "__main__":
    db.init_db()
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    if command == "on":
        if not turn_on()["changed"]:
            print("(already on)")
    elif command == "off":
        result = turn_off()
        if result["changed"]:
            s = result["session"]
            print(f"Ended session #{s['id']}: {to_local_display(s['started_at'])} → {to_local_display(s['ended_at'])}")
        else:
            print("(already off)")
    elif command != "status":
        raise SystemExit("Usage: python -m shared.focus on | off | status")
    _print_status()
