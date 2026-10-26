"""What happens to one new message. Both listener modes call process_message().

Webhook mode passes only the id (webhook payloads carry ids, not text, so we fetch the message).
Polling mode already has the full message from the list call and passes it in.

Routing:
- a message we posted ourselves (app_posts)       → skip
- A typing in the Webex Assistant space           → the AI assistant (listener/assistant.py)
- A's message anywhere else                       → store as 'self' (summaries show both sides)
- everyone else                                   → triage → store → notify if high and focus is on

Triage order: rules → (no rule matched) @mention of A = high → AI triage (if on) → regular.

Run `python -m listener.pipeline` to process the latest message in your 3 most recently
active spaces (a quick test without webhooks or polling).
"""

from listener import assistant
from shared import config, db, events, focus, notifier, triage_ai
from shared import webex_client as wx
from shared.assistant_space import room_id as assistant_room_id
from shared.log import log
from shared.rules import evaluate
from shared.tools import message_view

# Room titles and people's names rarely change, so remember them instead of fetching per message.
_room_cache: dict[str, dict] = {}
_name_cache: dict[str, str] = {}


def _get_room(room_id: str) -> dict:
    if room_id not in _room_cache:
        _room_cache[room_id] = wx.get_room(room_id)
    return _room_cache[room_id]


def _display_name(person_id: str, fallback: str) -> str:
    if person_id not in _name_cache:
        try:
            _name_cache[person_id] = wx.get_person(person_id).get("displayName") or fallback
        except Exception:
            return fallback
    return _name_cache[person_id]


def my_id() -> str:
    """A's personId, saved by scripts/login.py."""
    person_id = db.kv_get("my_person_id")
    if not person_id:
        raise SystemExit("Not logged in. Run: python -m scripts.login")
    return person_id


def triage(row: dict) -> tuple[str, str, str]:
    """(category, reason, decided_by) for a message from someone else."""
    # Rules are read on every message, so changes from chat, the UI, or MCP apply immediately.
    category, reason, decided_by = evaluate(row, db.list_rules(enabled_only=True))
    if decided_by == "default" and not row["mentioned_me"] and triage_ai.enabled():
        decided = triage_ai.classify(row)
        if decided:
            return decided
    return category, reason, decided_by


def process_message(message_id: str, message: dict | None = None) -> str:
    """Fetch (if needed), route, categorize, and store one message; notify A if it's high and focus is on.

    Returns what happened, for logging and tests: 'duplicate', 'skipped:own-post',
    'assistant', 'skipped:assistant-space', 'self', 'high', or 'regular'.
    """
    if db.message_exists(message_id):
        return "duplicate"
    # Take the posting lock so a post that is mid-way through "send, then record id" finishes first.
    with wx.post_lock:
        if db.is_app_post(message_id):
            return "skipped:own-post"

    msg = message or wx.get_message(message_id)
    me = my_id()

    if msg["roomId"] == assistant_room_id():
        if msg["personId"] == me:
            assistant.on_user_message(msg)
            return "assistant"
        return "skipped:assistant-space"

    room = _get_room(msg["roomId"])
    mentioned_me = me in msg.get("mentionedPeople", []) or "all" in msg.get("mentionedGroups", [])

    text = msg.get("text", "")
    if msg.get("files"):
        text = f"{text} [attachment]".strip()

    row = {
        "id": msg["id"],
        "room_id": msg["roomId"],
        "room_title": room.get("title", ""),
        "room_type": msg.get("roomType", room.get("type", "")),
        "person_id": msg["personId"],
        "person_email": msg.get("personEmail", ""),
        "person_name": _display_name(msg["personId"], msg.get("personEmail", "")),
        "text": text,
        "created": msg["created"],
        "mentioned_me": int(mentioned_me),
        # Recorded per message so the Triage tab and summaries can tell "missed during focus" apart.
        "focus_on": int(focus.is_on()),
    }

    if msg["personId"] == me:
        # A's own messages: kept for summary context, never triaged or notified.
        row["category"], row["reason"], row["decided_by"] = "self", "self", "self"
    else:
        row["category"], row["reason"], row["decided_by"] = triage(row)

    if not db.insert_message(row):
        return "duplicate"  # another delivery of the same message won the race

    should_notify = row["category"] == "high" and row["focus_on"]
    quiet_note = "  [focus off: no ping]" if row["category"] == "high" and not should_notify else ""
    preview = text if len(text) <= 60 else text[:57] + "..."
    log(f"[{row['category']}] {row['person_email'] or '?'} in {row['room_title'] or '?'}: {preview!r}"
        f"  ({row['reason']}){quiet_note}")

    if should_notify:
        delivered = notifier.notify(row)  # failures are logged inside; the message is stored either way
        if not delivered:
            log(f"[warn] no notify channel worked for {row['id']} (NOTIFY_CHANNELS={','.join(config.NOTIFY_CHANNELS)})")
    events.publish("message_stored", message_view(db.get_message(row["id"])))
    return row["category"]


if __name__ == "__main__":
    for room in wx.list_rooms(max_items=3):
        latest = wx.list_messages(room["id"], max_items=1)
        if not latest:
            print(f"(no messages in {room['title']})")
            continue
        # Pass only the id, like webhook mode does, so the fetch path gets tested too.
        outcome = process_message(latest[0]["id"])
        print(f"  -> {room['title']}: {outcome}")
