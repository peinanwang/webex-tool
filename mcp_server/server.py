"""Webex Focus MCP server: A's control panel from Claude Code / VS Code Copilot.

The IDE starts this file as a child process and talks to it over stdin/stdout (stdio transport).
It never calls Webex; it only reads and writes the SQLite DB the listener fills, so it works
even when the listener is stopped. Rule changes apply to the very next message, because the
listener re-reads rules for every message.

Never print() here: stdout is the MCP channel, and stray output would corrupt it.

Registered in .mcp.json (Claude Code) and .vscode/mcp.json (Copilot).
"""

import sys
from datetime import timedelta
from pathlib import Path

# The IDE may launch us from any working directory, so make the project root importable
# (for `shared.*`) before importing it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from shared import db  # noqa: E402
from shared.config import DIGESTS_DIR  # noqa: E402
from shared.rules import describe, evaluate  # noqa: E402
from shared.timeutil import period_bounds, period_label, to_local_display, to_webex_utc  # noqa: E402

mcp = MCPServer(
    "webex-focus",
    instructions=(
        "Webex Focus keeps the user's Webex quiet. A listener stores every message with a status: "
        "notify (Priority bot pinged the user), digest (held for the summary), ignore (held, left out of "
        "summaries), self (sent by the user). Use these tools to manage the user's rules, look up messages, "
        "and write summaries. Dates and times are in the user's local time."
    ),
)

db.init_db()


def _rule_view(rule: dict) -> dict:
    return {"id": rule["id"], "action": rule["action"], "match_type": rule["match_type"],
            "value": rule["value"], "enabled": bool(rule["enabled"]), "label": describe(rule)}


def _period_text(start_dt, end_dt) -> str:
    # end is exclusive internally; show the last included minute so "21 to 22" reads as "...22 23:59".
    return f"{start_dt:%Y-%m-%d %H:%M} to {end_dt - timedelta(seconds=1):%Y-%m-%d %H:%M}"


def _message_view(row: dict) -> dict:
    return {"time": to_local_display(row["created"]), "space": row["room_title"],
            "space_type": row["room_type"], "sender": row["person_email"], "text": row["text"],
            "status": row["status"], "reason": row["reason"], "mentioned_me": bool(row["mentioned_me"])}


# --- Rules (Phase 5) ---

@mcp.tool()
def list_rules() -> list[dict]:
    """List all of the user's rules (enabled and disabled), oldest first."""
    return [_rule_view(r) for r in db.list_rules()]


@mcp.tool()
def add_rule(action: str, match_type: str, value: str = "") -> dict:
    """Add a rule. It applies to the next incoming message.

    action: 'notify' (Priority bot pings the user), 'digest' (hold silently for the summary),
            or 'ignore' (hold silently, leave out of summaries).
    match_type: 'sender' (value = sender email), 'space' (value = space title, exact),
                'keyword' (value = text to look for, case-insensitive), or 'mention' (no value;
                matches when the user is @mentioned).
    When several rules match one message, ignore beats notify beats digest. If no rule matches,
    @mentions notify and everything else goes to digest.
    """
    try:
        return _rule_view(db.add_rule(action, match_type, value))
    except ValueError as exc:
        # Return the reason as data so the assistant can explain it or retry with fixed input.
        return {"error": str(exc)}


@mcp.tool()
def delete_rule(rule_id: int) -> str:
    """Delete a rule by id (see list_rules)."""
    return f"Deleted rule {rule_id}." if db.delete_rule(rule_id) else f"No rule with id {rule_id}."


@mcp.tool()
def set_rule_enabled(rule_id: int, enabled: bool) -> str:
    """Turn a rule off (enabled=false) or back on without deleting it."""
    if not db.set_rule_enabled(rule_id, enabled):
        return f"No rule with id {rule_id}."
    return f"Rule {rule_id} {'enabled' if enabled else 'disabled'}."


@mcp.tool()
def test_rule(text: str, sender_email: str = "", space: str = "", mentioned: bool = False) -> dict:
    """Dry run: what would happen to a message like this with the current rules? Nothing is stored or sent.

    Use it to answer questions like "if C writes 'server down' in Team Chat, would I get pinged?"
    """
    message = {"person_email": sender_email, "room_title": space, "room_id": "", "text": text,
               "mentioned_me": int(mentioned)}
    action, reason = evaluate(message, db.list_rules(enabled_only=True))
    return {"action": action, "reason": reason, "would_ping": action == "notify"}


# --- Messages (Phase 5) ---

@mcp.tool()
def get_messages(status: str = "", sender: str = "", space: str = "", start: str = "", end: str = "",
                 limit: int = 50) -> dict:
    """Search stored messages, newest first.

    status: '', 'notify', 'digest', 'ignore', or 'self' ('' = any).
    sender / space: partial, case-insensitive match on sender email / space title.
    start / end: local date ('2026-10-21') or date-time ('2026-10-21T14:00'). A date as `end`
                 includes that whole day. Both empty = today so far. Only start = until now.
    Use the `reason` field to explain why a message was or wasn't relayed.
    """
    start_dt, end_dt = period_bounds(start or None, end or None)
    rows = db.query_messages(statuses=[status] if status else None, sender=sender or None,
                             space=space or None, start_utc=to_webex_utc(start_dt),
                             end_utc=to_webex_utc(end_dt), limit=min(limit, 500))
    oldest = db.oldest_message_time()
    return {
        "period": _period_text(start_dt, end_dt),
        "count": len(rows),
        "messages": [_message_view(r) for r in rows],
        "data_starts_at": to_local_display(oldest) if oldest else None,
    }


# --- Digest (Phase 6) ---

DIGEST_LIMIT = 500


@mcp.tool()
def get_digest_input(start: str = "", end: str = "", scope: str = "held", include_ignored: bool = False) -> dict:
    """Messages to summarize for a period, grouped by space, oldest first.

    scope: 'held' = what the user missed (digest messages, plus ignore if include_ignored);
           'all'  = everything stored, including relayed (notify) messages and the user's own (self),
                    so conversations show both sides.
    start / end: local date or date-time; empty = today so far. A date as `end` includes that whole day.
    After summarizing, call save_digest with the same start, end, and scope.
    """
    if scope not in ("held", "all"):
        return {"error": "scope must be 'held' or 'all'"}
    statuses = ["digest"] + (["ignore"] if include_ignored else []) if scope == "held" else None
    start_dt, end_dt = period_bounds(start or None, end or None)
    start_utc, end_utc = to_webex_utc(start_dt), to_webex_utc(end_dt)

    rows = db.query_messages(statuses=statuses, start_utc=start_utc, end_utc=end_utc,
                             limit=DIGEST_LIMIT + 1, newest_first=False)
    truncated = len(rows) > DIGEST_LIMIT
    rows = rows[:DIGEST_LIMIT]

    spaces: dict[str, dict] = {}
    for row in rows:
        group = spaces.setdefault(row["room_id"], {"space": row["room_title"], "space_type": row["room_type"],
                                                   "messages": []})
        view = _message_view(row)
        del view["space"], view["space_type"]
        group["messages"].append(view)

    oldest = db.oldest_message_time()
    return {
        "period": _period_text(start_dt, end_dt),
        "scope": scope,
        "counts_in_period": db.count_by_status(start_utc, end_utc),
        "message_count": len(rows),
        "truncated": truncated,
        "data_starts_at": to_local_display(oldest) if oldest else None,
        "note": "No data exists before data_starts_at (the listener wasn't running yet).",
        "spaces": list(spaces.values()),
    }


@mcp.tool()
def save_digest(markdown: str, start: str = "", end: str = "", scope: str = "held") -> str:
    """Save a summary as data/digests/<period>_<scope>.md (overwrites the same period + scope).

    Pass the same start, end, and scope used for get_digest_input.
    """
    if scope not in ("held", "all"):
        return "Error: scope must be 'held' or 'all'."
    start_dt, end_dt = period_bounds(start or None, end or None)
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGESTS_DIR / f"{period_label(start_dt, end_dt)}_{scope}.md"
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return f"Saved {path}"


@mcp.tool()
def list_digests() -> list[str]:
    """File names of saved digests, newest first."""
    if not DIGESTS_DIR.exists():
        return []
    return sorted((p.name for p in DIGESTS_DIR.glob("*.md")), reverse=True)


@mcp.tool()
def read_digest(filename: str) -> str:
    """Read a saved digest by file name (from list_digests)."""
    path = DIGESTS_DIR / Path(filename).name  # .name blocks paths like ../../.env
    if not path.exists():
        return f"No digest named {filename}. Use list_digests to see what exists."
    return path.read_text(encoding="utf-8")


@mcp.prompt()
def daily_digest(start: str = "", end: str = "", scope: str = "held") -> str:
    """Summarize Webex messages for a period (default: what I missed today)."""
    return (
        f"Summarize my Webex messages. Call get_digest_input with start={start!r}, end={end!r}, scope={scope!r}.\n"
        "Then write a concise Markdown summary:\n"
        "- A title with the period, and one line of counts (relayed vs. held vs. ignored).\n"
        "- One section per space, most important first. Bullet the key points; name who said what.\n"
        "- An 'Action items for me' section: questions, requests, or deadlines addressed to me.\n"
        "- If data_starts_at is after the requested start, say there's no data before then.\n"
        "- If truncated is true, say the summary covers only the first messages.\n"
        f"Finally call save_digest with the Markdown and the same start, end, and scope, and tell me the file path."
    )


if __name__ == "__main__":
    mcp.run()  # stdio transport
