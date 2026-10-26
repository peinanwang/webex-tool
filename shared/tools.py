"""The one tool registry: everything the assistant (and the UI, and Claude Code via MCP) can do.

A "tool" is a plain Python function. @tool registers it with:
- a description (the docstring; the model reads it to decide when to call the tool),
- a JSON Schema for its arguments (built from the type hints by pydantic).

Every tool returns {"data": ..., "display": <text rendered from templates/chat/...>, "cards": [...]}.
`display` is the ready-made reply (so wording comes from templates), `data` is for the model and the
UI, and `cards` are rich UI widgets. On bad input a tool raises ToolError; call() turns that into
{"error": ..., "display": ...} so the model can explain or retry.

Keep descriptions short and concrete with an example: older models pick tools worse with long text.
"""

import inspect
from dataclasses import dataclass
from typing import Callable, Literal

from pydantic import ValidationError, create_model

from shared import db, focus, summary, triage_ai
from shared.log import log
from shared.notifier import message_card
from shared.rules import describe, evaluate
from shared.templates import render
from shared.timeutil import describe_period, now_webex_utc, parse_webex, period_bounds, short_local, to_webex_utc


class ToolError(Exception):
    """Bad input or a missing thing; the message is shown to the user."""


@dataclass
class Tool:
    name: str
    fn: Callable
    description: str
    schema: dict
    args_model: type


TOOLS: dict[str, Tool] = {}


def _clean_schema(schema: dict) -> dict:
    """Drop pydantic's 'title' noise; models don't need it."""
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)
    return schema


def tool(fn: Callable) -> Callable:
    params = inspect.signature(fn).parameters
    fields = {name: (p.annotation, ... if p.default is inspect.Parameter.empty else p.default)
              for name, p in params.items()}
    args_model = create_model(f"{fn.__name__}_args", **fields)
    TOOLS[fn.__name__] = Tool(fn.__name__, fn, inspect.getdoc(fn) or "",
                              _clean_schema(args_model.model_json_schema()), args_model)
    return fn


def call(name: str, args: dict | None = None) -> dict:
    """Run a tool by name with validated arguments. Never raises."""
    entry = TOOLS.get(name)
    if not entry:
        return _error(f"There's no tool called {name}.")
    try:
        validated = entry.args_model(**(args or {}))
        return entry.fn(**validated.model_dump())
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return _error(f"Invalid arguments for {name}: {problems}")
    except (ToolError, ValueError) as exc:
        return _error(str(exc))
    except Exception as exc:
        log(f"[error] tool {name} failed: {exc!r}")
        return _error(f"Something went wrong running {name}: {exc}")


def _error(message: str) -> dict:
    return {"error": message, "display": render("chat/error.md", message=message), "data": None, "cards": []}


def openai_specs() -> list[dict]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.schema}}
            for t in TOOLS.values()]


def result(display: str, data=None, cards: list | None = None) -> dict:
    return {"data": data, "display": display, "cards": cards or []}


# --- views (plain dicts for templates, the UI, and the model) ---

def rule_view(rule: dict) -> dict:
    return {"id": rule["id"], "category": rule["category"], "match_type": rule["match_type"],
            "value": rule["value"], "enabled": bool(rule["enabled"]), "label": describe(rule)}


def rule_card(rule: dict) -> dict:
    return {"type": "rule", **rule_view(rule)}


def message_view(row: dict) -> dict:
    return {"id": row["id"], "time": short_local(row["created"]), "created": row["created"],
            "sender": row.get("person_name") or row.get("person_email") or "?",
            "sender_email": row.get("person_email") or "", "space": row.get("room_title") or "",
            "is_direct": row.get("room_type") == "direct", "text": row.get("text") or "",
            "category": row["category"], "reason": row["reason"], "decided_by": row["decided_by"],
            "mentioned_me": bool(row["mentioned_me"]), "focus_on": bool(row["focus_on"]),
            "notified": bool(row.get("notified_at")), "feedback": row.get("feedback")}


def _period(start: str, end: str):
    try:
        return period_bounds(start or None, end or None)
    except ValueError:
        raise ToolError("Dates must look like 2026-10-26 or 2026-10-26T14:00.") from None


def focus_view() -> dict:
    s = focus.status()
    view = {"on": s["on"], "session_id": s["session_id"], "counts": s["counts"],
            "since": short_local(s["since"]) if s["since"] else None, "since_utc": s["since"]}
    if s["on"]:
        minutes = int((parse_webex(now_webex_utc()) - parse_webex(s["since"])).total_seconds() // 60)
        view["duration"] = f"{minutes // 60}h {minutes % 60}m" if minutes >= 60 else f"{minutes}m"
    return view


# === Focus mode ===

@tool
def get_focus_status() -> dict:
    """Is focus mode on, since when, and how many high/regular messages arrived this session.
    Example: "Am I in focus mode?" or "How much have I missed?"."""
    view = focus_view()
    return result(render("chat/focus_status.md", **view), view)


@tool
def set_focus_mode(on: bool) -> dict:
    """Turn focus mode on (high-priority messages notify me) or off (nothing notifies; a summary of
    what I missed is posted automatically). Example: "focus on", "I'm done focusing" -> on=false."""
    from shared import events
    if on:
        changed = focus.turn_on()["changed"]
        view = focus_view()
        events.publish("focus_changed", view)
        return result(render("chat/focus_on.md", already=not changed, **view), view)
    outcome = focus.turn_off()
    session = outcome["session"]
    if outcome["changed"]:
        summary.summarize_session_in_background(session["id"])
    view = focus_view()
    events.publish("focus_changed", view)
    values = {"already": not outcome["changed"],
              "session_period": describe_period(parse_webex(session["started_at"]), parse_webex(session["ended_at"]))
              if session else ""}
    return result(render("chat/focus_off.md", **values), {**view, **values})


# === Rules ===

@tool
def list_rules() -> dict:
    """List all my rules (with ids and on/off state). Use it to find a rule's id before changing it."""
    rules = [rule_view(r) for r in db.list_rules()]
    return result(render("chat/rules_list.md", rules=rules), rules,
                  [rule_card(r) for r in db.list_rules()])


@tool
def add_rule(category: Literal["high", "regular"],
             match_type: Literal["sender", "space", "keyword", "mention", "topic"], value: str = "") -> dict:
    """Add a triage rule. category: 'high' (notify me) or 'regular' (hold for the summary).
    match_type: 'sender' (value = an email; use find_contacts first if you only have a name),
    'space' (value = exact space title; use find_spaces), 'keyword' (value = word in the text),
    'mention' (no value; when I'm @mentioned), 'topic' (value = a subject in plain words, judged by AI).
    Example: "notify me when Bob writes" -> find_contacts("Bob"), then add_rule("high", "sender", "bob@x.com")."""
    try:
        rule = db.add_rule(category, match_type, value)
    except ValueError as exc:
        raise ToolError(str(exc)) from None
    view = rule_view(rule)
    return result(render("chat/rule_added.md", rule=view), view, [rule_card(rule)])


@tool
def set_rule_enabled(rule_id: int, enabled: bool) -> dict:
    """Pause (enabled=false) or resume (enabled=true) a rule without deleting it. Use list_rules for ids."""
    if not db.set_rule_enabled(rule_id, enabled):
        raise ToolError(f"There's no rule #{rule_id}. Say \"show my rules\" to see them.")
    rule = db.get_rule(rule_id)
    return result(render("chat/rule_toggled.md", rule=rule_view(rule)), rule_view(rule), [rule_card(rule)])


@tool
def delete_rule(rule_id: int, confirm: bool = False) -> dict:
    """Delete a rule. First call with confirm=false: it asks the user to confirm. Only after the user
    says yes, call again with confirm=true."""
    rule = db.get_rule(rule_id)
    if not rule:
        raise ToolError(f"There's no rule #{rule_id}. Say \"show my rules\" to see them.")
    if not confirm:
        return result(render("chat/rule_delete_confirm.md", rule=rule_view(rule)),
                      {"needs_confirmation": True, "rule": rule_view(rule)})
    db.delete_rule(rule_id)
    return result(render("chat/rule_removed.md", rule=rule_view(rule)), {"deleted": rule_view(rule)})


@tool
def test_rule(text: str, sender_email: str = "", space: str = "", mentioned: bool = False) -> dict:
    """Dry run with my current rules (no AI): what category would a message like this get, and why?
    Nothing is stored. Example: "if carol@x.com says 'server down' in Team Chat, would I get pinged?"."""
    message = {"person_email": sender_email, "room_title": space, "room_id": "", "text": text,
               "mentioned_me": int(mentioned)}
    category, reason, decided_by = evaluate(message, db.list_rules(enabled_only=True))
    data = {"category": category, "reason": reason, "decided_by": decided_by,
            "ai_would_decide": decided_by == "default" and not mentioned and triage_ai.enabled(),
            "focus_on": focus.is_on(), "text": text, "sender": sender_email, "space": space}
    return result(render("chat/rule_test.md", **data), data)


@tool
def find_contacts(query: str) -> dict:
    """Look up people by part of their name or email (people who messaged me, then the Webex directory).
    Use before add_rule(sender) when you only have a name."""
    people = db.known_contacts(query)
    if not people and len(query) >= 3:
        from shared import webex_client as wx
        try:
            people = [{"email": p["emails"][0], "name": p.get("displayName"), "messages": 0}
                      for p in wx.search_people(query) if p.get("emails")]
        except Exception as exc:
            log(f"[warn] Webex people search failed: {exc}")
    return result(render("chat/contacts.md", query=query, people=people), people)


@tool
def find_spaces(query: str = "") -> dict:
    """Look up spaces I've received messages in, by part of the title. Use before add_rule(space)."""
    spaces = db.known_spaces(query)
    return result(render("chat/spaces.md", query=query, spaces=spaces), spaces)


# === Messages & triage ===

@tool
def search_messages(category: Literal["", "high", "regular", "self"] = "", sender: str = "", space: str = "",
                    contains: str = "", start: str = "", end: str = "", limit: int = 20) -> dict:
    """Find stored messages, newest first. category: 'high', 'regular', 'self' (sent by me) or '' for any.
    sender / space / contains: partial text. start / end: local date '2026-10-26' or '2026-10-26T14:00';
    both empty = today. Each result has an id (for mark_message) and the reason it was categorized.
    Example: "what did Carol say today?" -> search_messages(sender="carol")."""
    start_dt, end_dt = _period(start, end)
    rows = db.query_messages(categories=[category] if category else None, sender=sender or None,
                             space=space or None, contains=contains or None, start_utc=to_webex_utc(start_dt),
                             end_utc=to_webex_utc(end_dt), limit=max(1, min(limit, 100)))
    messages = [message_view(r) for r in rows]
    period = describe_period(start_dt, end_dt)
    data = {"period": period, "count": len(messages), "messages": messages}
    return result(render("chat/messages_list.md", **data), data, [message_card(r) for r in rows[:5]])


@tool
def get_triage_stats(start: str = "", end: str = "") -> dict:
    """How many messages were high vs. regular, how many I reviewed, and how accurate triage was
    (based on my corrections). Dates like search_messages; empty = today."""
    start_dt, end_dt = _period(start, end)
    stats = db.triage_stats(to_webex_utc(start_dt), to_webex_utc(end_dt))
    stats["period"] = describe_period(start_dt, end_dt)
    return result(render("chat/triage_stats.md", **stats), stats)


@tool
def mark_message(message_id: str, label: Literal["correct", "should_be_high", "should_be_regular"]) -> dict:
    """Record my verdict on how a message was categorized (improves AI triage). Get the id from
    search_messages. Example: "Carol's last message was actually important" -> label='should_be_high'."""
    try:
        row = db.set_feedback(message_id, label)
    except ValueError as exc:
        raise ToolError(str(exc)) from None
    if not row:
        raise ToolError("I couldn't find that message. Try searching for it first.")
    from shared import events
    view = message_view(row)
    events.publish("message_updated", view)
    return result(render("chat/feedback_saved.md", message=view), view, [message_card(row)])


# === Summaries ===

@tool
def summarize(start: str = "", end: str = "", scope: Literal["held", "all"] = "held") -> dict:
    """Write and save a summary. scope 'held' = only regular messages ("what did I miss?");
    'all' = everything incl. high messages and my replies ("what happened?"). start / end: local
    dates like '2026-10-26'; both empty = today so far. Example: "summarize Monday to Wednesday"."""
    start_dt, end_dt = _period(start, end)
    row = summary.generate(start_dt, end_dt, scope, "on_demand")
    return result(row["markdown"], summary.summary_view(row), [summary.summary_card(row)])


@tool
def list_summaries(kind: Literal["", "on_demand", "focus_session", "end_of_day"] = "", limit: int = 10) -> dict:
    """List saved summaries, newest first. kind: 'on_demand', 'focus_session', 'end_of_day', or '' for all."""
    rows = [summary.summary_view(r) for r in db.list_summaries(kind or None, max(1, min(limit, 50)))]
    for r in rows:
        del r["markdown"]
    return result(render("chat/summaries_list.md", summaries=rows), rows)


@tool
def get_summary(summary_id: int) -> dict:
    """Show one saved summary by id (see list_summaries)."""
    row = db.get_summary(summary_id)
    if not row:
        raise ToolError(f"There's no summary #{summary_id}.")
    return result(row["markdown"], summary.summary_view(row), [summary.summary_card(row)])


@tool
def email_summary(summary_id: int) -> dict:
    """Email a saved summary to me. (For now this writes the email to the outbox folder.)"""
    from shared import emailer
    row = db.get_summary(summary_id)
    if not row:
        raise ToolError(f"There's no summary #{summary_id}.")
    where = emailer.send_summary(row)
    data = {"summary_id": summary_id, "to": emailer.recipient(), "outbox_path": where}
    return result(render("chat/email_sent.md", **data), data)


# === What I pay attention to: focus profile, watched keywords and topics ===

def _watches() -> dict:
    """Keyword and topic rules (what A explicitly watches for), split by kind."""
    rules = [rule_view(r) for r in db.list_rules() if r["match_type"] in ("keyword", "topic")]
    return {"keywords": [r for r in rules if r["match_type"] == "keyword"],
            "topics": [r for r in rules if r["match_type"] == "topic"]}


def _profile_data() -> dict:
    return {"profile": triage_ai.get_profile(), "ai_triage_on": triage_ai.enabled(),
            "corrections": db.count_feedback(), **_watches()}


@tool
def get_focus_profile() -> dict:
    """Show what I pay attention to: my focus profile (what's urgent to me, used by AI triage), the
    keywords and topics I watch, and how many corrections the AI has learned from."""
    data = _profile_data()
    return result(render("chat/focus_profile.md", updated=False, **data), data)


@tool
def set_focus_profile(text: str) -> dict:
    """Replace my focus profile. Example: "outages and anything from my manager are urgent; social
    chat isn't". Keep the user's own words as much as possible."""
    if len(text.strip()) < 10:
        raise ToolError("The focus profile should be a sentence or two about what's urgent for you.")
    triage_ai.set_profile(text)
    data = _profile_data()
    return result(render("chat/focus_profile.md", updated=True, **data), data)


@tool
def explain_focus_profile() -> dict:
    """The AI's own summary of what it treats as urgent for me vs. what can wait, based on my focus
    profile, rules, and corrections. Example: "what do you think is important to me?"."""
    explained = triage_ai.explain()
    data = {"profile": triage_ai.get_profile(), "ai_written": explained is not None,
            "urgent": [], "can_wait": [], "learned": [], **(explained or {})}
    return result(render("chat/profile_explained.md", **data), data)


@tool
def list_watches() -> dict:
    """List the keywords and topics I watch (keyword = exact text in a message; topic = a subject the
    AI judges). Example: "what words am I watching?"."""
    data = _watches()
    return result(render("chat/watch_list.md", **data), data)


@tool
def watch(text: str, kind: Literal["keyword", "topic"] = "keyword") -> dict:
    """Always notify me about messages with this keyword (exact text, case-insensitive) or about this
    topic (judged by AI). Example: "watch for the word outage" -> watch("outage");
    "tell me about anything on the Q3 launch" -> watch("the Q3 launch", "topic")."""
    text = text.strip()
    existing = next((r for r in db.list_rules() if r["match_type"] == kind and r["value"].lower() == text.lower()), None)
    if existing:
        if not existing["enabled"]:
            db.set_rule_enabled(existing["id"], True)
        view = rule_view(db.get_rule(existing["id"]))
        return result(render("chat/watch_added.md", rule=view, already=True), view, [rule_card(view)])
    try:
        rule = db.add_rule("high", kind, text)
    except ValueError as exc:
        raise ToolError(str(exc)) from None
    view = rule_view(rule)
    return result(render("chat/watch_added.md", rule=view, already=False), view, [rule_card(rule)])


@tool
def unwatch(text: str) -> dict:
    """Stop watching a keyword or topic (removes that keyword/topic rule). Example: "stop watching outage"."""
    matches = [r for r in db.list_rules()
               if r["match_type"] in ("keyword", "topic") and r["value"].lower() == text.strip().lower()]
    if not matches:
        raise ToolError(f"You're not watching \"{text.strip()}\". Type /watch to see what you're watching.")
    for r in matches:
        db.delete_rule(r["id"])
    views = [rule_view(r) for r in matches]
    return result(render("chat/watch_removed.md", rules=views), views)


# --- helpers used by the UI API (not exposed to the model) ---

def preview_rule(category: str, match_type: str, value: str) -> dict:
    """Which of today's messages would change category if this rule existed? (Topic rules need AI: skipped.)"""
    try:
        category, match_type, value = db.validate_rule(category, match_type, value)
    except ValueError as exc:
        raise ToolError(str(exc)) from None
    if match_type == "topic":
        return {"supported": False, "changed": [], "checked": 0}
    start_dt, end_dt = period_bounds(None, None)
    rows = [r for r in db.query_messages(start_utc=to_webex_utc(start_dt), end_utc=to_webex_utc(end_dt), limit=1000)
            if r["category"] != "self"]
    rules = db.list_rules(enabled_only=True)
    candidate = {"id": max([r["id"] for r in rules], default=0) + 1, "category": category,
                 "match_type": match_type, "value": value, "enabled": 1}
    changed = []
    for row in rows:
        new_category, new_reason, decided_by = evaluate(row, rules + [candidate])
        if decided_by == "default" and row["decided_by"] == "ai":
            continue  # no rule matched; the AI's decision would stand
        if new_category != row["category"]:
            changed.append({**message_view(row), "new_category": new_category, "new_reason": new_reason})
    return {"supported": True, "changed": changed, "checked": len(rows)}
