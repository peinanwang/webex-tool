"""What happens to one new message. Both listener modes call process_message().

Webhook mode passes only the id (webhook payloads carry ids, not text, so we fetch the message).
Polling mode already has the full message from the list call and passes it in.

Run `python -m listener.pipeline` to process the latest message in your 3 most recently
active spaces (a quick test without webhooks or polling).
"""

from shared import webex_client as wx
from shared.db import insert_message, kv_get, list_rules, mark_relayed, message_exists
from shared.rules import evaluate

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


def relay(row: dict) -> None:
    """Priority bot pings A in their 1:1 with the bot (the one space A keeps unmuted)."""
    sender = _display_name(row["person_id"], row["person_email"])
    where = "a direct message" if row["room_type"] == "direct" else f"**{row['room_title']}**"
    markdown = f"🔔 **{sender}** in {where}:\n\n{row['text']}\n\n_why: {row['reason']}_"
    wx.bot_send(markdown, to_person_email=kv_get("my_email"))
    mark_relayed(row["id"])


def my_ids() -> tuple[str, str]:
    """A's and the Priority bot's personIds, saved by scripts/login.py."""
    my_id, bot_id = kv_get("my_person_id"), kv_get("bot_person_id")
    if not my_id or not bot_id:
        raise SystemExit("Not logged in. Run: python -m scripts.login")
    return my_id, bot_id


def process_message(message_id: str, message: dict | None = None) -> str:
    """Fetch (if needed), classify, and store one message.

    Returns what happened, for logging and tests:
    'duplicate', 'skipped:bot', 'self', 'notify', 'digest', or 'ignore'.
    """
    if message_exists(message_id):
        return "duplicate"

    msg = message or wx.get_message(message_id)
    my_id, bot_id = my_ids()

    # Our own notifications come back through the webhook too; ignore them to avoid loops.
    if msg["personId"] == bot_id:
        return "skipped:bot"

    room = _get_room(msg["roomId"])
    mentioned_me = my_id in msg.get("mentionedPeople", []) or "all" in msg.get("mentionedGroups", [])

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
        "text": text,
        "created": msg["created"],
        "mentioned_me": int(mentioned_me),
    }

    if msg["personId"] == my_id:
        # A's own messages: kept for summary context, never run through rules or relayed.
        row["status"], row["reason"] = "self", "self"
    else:
        # Rules are read on every message, so changes made through MCP apply immediately.
        row["status"], row["reason"] = evaluate(row, list_rules(enabled_only=True))

    if not insert_message(row):
        return "duplicate"  # another delivery of the same message won the race

    preview = text if len(text) <= 60 else text[:57] + "..."
    print(f"[{row['status']}] {row['person_email'] or '?'} in {row['room_title'] or '?'}: {preview!r}"
          f"  ({row['reason']})", flush=True)

    if row["status"] == "notify":
        try:
            relay(row)
        except Exception as exc:
            # The message is still stored; only the ping failed.
            print(f"[error] relay failed for {row['id']}: {exc}", flush=True)
    return row["status"]


if __name__ == "__main__":
    for room in wx.list_rooms(max_items=3):
        latest = wx.list_messages(room["id"], max_items=1)
        if not latest:
            print(f"(no messages in {room['title']})")
            continue
        # Pass only the id, like webhook mode does, so the fetch path gets tested too.
        outcome = process_message(latest[0]["id"])
        print(f"  -> {room['title']}: {outcome}")
