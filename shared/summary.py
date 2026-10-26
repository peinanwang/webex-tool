"""Summaries of any period: on demand, when focus mode turns off, and at the end of the day.

How one is made:
1. build_input(): the stored messages for the period, grouped by space, oldest first.
2. The LLM returns structured JSON (headline, highlights, by_space, action_items) through
   llm.extract(), guided by templates/prompts/summarize.md.
3. templates/summary/summary.md turns that JSON into the final text. The model decides *what* to
   say, and the template decides *how it looks*.
4. The result is saved in the `summaries` table.

Without an LLM (no key, or the API is down) we still produce a summary: the same template, filled
with the latest messages per space instead of AI-written points.

Scopes: 'held' = regular messages only ("what I missed"); 'all' = everything, including high
messages and A's own replies ("what happened").
"""

import json
import threading
from datetime import date, datetime, timedelta

from shared import config, db, events, llm
from shared.log import log
from shared.templates import render
from shared.timeutil import (day_start, describe_period, parse_webex, short_local, to_local_display,
                             to_webex_utc)

MAX_MESSAGES = 300   # older gateway models have smaller context windows
KIND_LABELS = {"on_demand": "Summary", "focus_session": "While you were focused", "end_of_day": "End of day"}

SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "One sentence: the most important thing in this period."},
        "highlights": {"type": "array", "items": {"type": "string"},
                       "description": "2-5 key points across all spaces, most important first."},
        "by_space": {"type": "array", "description": "One entry per space that had something worth noting.",
                     "items": {"type": "object", "properties": {
                         "space": {"type": "string"},
                         "points": {"type": "array", "items": {"type": "string"}}},
                         "required": ["space", "points"]}},
        "action_items": {"type": "array", "description": "Things the user needs to do or answer.",
                         "items": {"type": "object", "properties": {
                             "what": {"type": "string"}, "who": {"type": "string", "description": "who asked"},
                             "due": {"type": "string", "description": "deadline if stated, else empty"}},
                             "required": ["what", "who", "due"]}},
    },
    "required": ["headline", "highlights", "by_space", "action_items"],
}


def build_input(start_dt: datetime, end_dt: datetime, scope: str) -> dict:
    start_utc, end_utc = to_webex_utc(start_dt), to_webex_utc(end_dt)
    rows = db.query_messages(categories=["regular"] if scope == "held" else None, start_utc=start_utc,
                             end_utc=end_utc, limit=MAX_MESSAGES + 1, newest_first=False)
    truncated = len(rows) > MAX_MESSAGES
    rows = rows[:MAX_MESSAGES]
    spaces: dict[str, dict] = {}
    for row in rows:
        title = "Direct message with " + (row["room_title"] or "?") if row["room_type"] == "direct" else row["room_title"]
        group = spaces.setdefault(row["room_id"], {"space": title, "messages": []})
        group["messages"].append({
            "time": short_local(row["created"]),
            "sender": "me" if row["category"] == "self" else (row["person_name"] or row["person_email"]),
            "text": row["text"], "category": row["category"], "mentioned_me": bool(row["mentioned_me"])})
    oldest = db.oldest_message_time()
    return {
        "period": describe_period(start_dt, end_dt), "scope": scope,
        "counts": db.count_by_category(start_utc, end_utc),
        "message_count": len(rows), "truncated": truncated,
        "data_starts_at": to_local_display(oldest) if oldest and oldest > start_utc else None,
        "spaces": list(spaces.values()),
    }


def _fallback_data(inp: dict) -> dict:
    """No LLM: list the latest messages per space so the summary is still useful."""
    by_space = [{"space": s["space"],
                 "points": [f"{m['sender']}: {m['text'][:140]}" for m in s["messages"][-3:]]} for s in inp["spaces"]]
    return {"headline": f"{inp['message_count']} messages in {len(inp['spaces'])} spaces.",
            "highlights": [], "by_space": by_space, "action_items": [], "ai_written": False}


def _write(inp: dict, kind: str) -> tuple[str, dict | None]:
    common = {"kind": kind, "kind_label": KIND_LABELS[kind], "period": inp["period"], "scope": inp["scope"],
              "counts": inp["counts"], "truncated": inp["truncated"], "data_starts_at": inp["data_starts_at"]}
    if inp["message_count"] == 0:
        return render("summary/empty.md", **common), None
    data = None
    if llm.is_configured():
        try:
            data = llm.extract(render("prompts/summarize.md", scope=inp["scope"], kind=kind, period=inp["period"]),
                               json.dumps(inp, ensure_ascii=False), "submit_summary",
                               "Record the summary of these Webex messages.", SCHEMA)
            data["ai_written"] = True
        except llm.LLMUnavailable as exc:
            log(f"[summary] AI unavailable ({exc}); using the plain fallback")
    data = data or _fallback_data(inp)
    values = {**common, "headline": data.get("headline", ""), "highlights": data.get("highlights", []),
              "by_space": data.get("by_space", []), "action_items": data.get("action_items", []),
              "ai_written": data.get("ai_written", False)}
    return render("summary/summary.md", **values), data


def generate(start_dt: datetime, end_dt: datetime, scope: str = "held", kind: str = "on_demand") -> dict:
    """Make and save a summary. Returns the saved row (with `markdown`)."""
    if scope not in ("held", "all"):
        raise ValueError("scope must be 'held' or 'all'")
    markdown, data = _write(build_input(start_dt, end_dt, scope), kind)
    row = db.add_summary(kind, to_webex_utc(start_dt), to_webex_utc(end_dt), scope, markdown, data)
    events.publish("summary_created", summary_view(row))
    return row


def regenerate(summary_id: int) -> dict:
    row = db.get_summary(summary_id)
    if not row:
        raise ValueError(f"No summary with id {summary_id}.")
    markdown, data = _write(build_input(parse_webex(row["period_start"]), parse_webex(row["period_end"]),
                                        row["scope"]), row["kind"])
    db.update_summary(summary_id, markdown, data)
    row = db.get_summary(summary_id)
    events.publish("summary_created", summary_view(row))
    return row


def summary_view(row: dict) -> dict:
    return {"id": row["id"], "kind": row["kind"], "kind_label": KIND_LABELS[row["kind"]], "scope": row["scope"],
            "period": describe_period(parse_webex(row["period_start"]), parse_webex(row["period_end"])),
            "period_start": row["period_start"], "period_end": row["period_end"],
            "markdown": row["markdown"], "created": row["created_at"],
            "delivered_at": row["delivered_at"], "delivered_to": row["delivered_to"]}


def summary_card(row: dict) -> dict:
    v = summary_view(row)
    return {"type": "summary", "id": v["id"], "kind_label": v["kind_label"], "period": v["period"]}


# --- automatic triggers ---

def summarize_session(session_id: int) -> dict | None:
    """Focus mode turned off: summarize the regular messages from that session and post it."""
    from shared.assistant_space import post  # imported here to keep module imports one-directional
    session = db.get_focus_session(session_id)
    if not session or not session["ended_at"]:
        return None
    row = generate(parse_webex(session["started_at"]), parse_webex(session["ended_at"]), "held", "focus_session")
    db.set_session_summary(session_id, row["id"])
    post(render("chat/focus_off_summary.md", summary=row["markdown"], summary_id=row["id"],
                link=f"{config.UI_URL}/#/summaries?id={row['id']}"),
         role="notice", cards=[summary_card(row)])
    return row


def summarize_session_in_background(session_id: int) -> None:
    """Run summarize_session in a thread so the "focus is off" reply isn't held up by the LLM."""
    def run():
        try:
            summarize_session(session_id)
        except Exception as exc:
            log(f"[error] focus-session summary failed: {exc}")
    threading.Thread(target=run, daemon=True, name=f"session-summary-{session_id}").start()


def end_of_day(day: date) -> dict:
    """The daily summary: generate, "email" it (outbox), and post a copy in the Webex Assistant space."""
    from shared import emailer
    from shared.assistant_space import post
    row = generate(day_start(day), day_start(day + timedelta(days=1)), config.EOD_SCOPE, "end_of_day")
    where = emailer.send_summary(row)
    post(render("chat/eod_posted.md", summary=row["markdown"], outbox_path=where, day=day.strftime("%a %b %d")),
         role="notice", cards=[summary_card(row)])
    db.kv_set("eod_last_date", day.isoformat())
    return row
