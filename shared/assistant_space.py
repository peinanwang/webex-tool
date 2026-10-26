"""A's "Webex Assistant" space: the chat interface for the assistant, and where alerts land.

A creates this space by hand in Webex (only A in it) and puts its title in .env
(ASSISTANT_SPACE_TITLE, default "Webex Assistant"). The server finds it by that title.

Everything we post there is sent *as A* (through A's integration login), so Webex shows A as the
sender of both A's own messages and the assistant's. To tell them apart, every post from the server
is wrapped by templates/chat/space_post.md, which adds a header like "🤖 **Webex Assistant**".
A's own messages have no header.

post() does three things:
1. posts into Webex as A and records the id in app_posts (so polling skips it),
2. stores the turn in chat_messages (the UI's Assistant tab shows the same thread, without the header),
3. publishes a live event for open UI tabs.
"""

from shared import config, db, events
from shared import webex_client as wx
from shared.log import log
from shared.templates import render


class SpaceNotFound(Exception):
    """No space with ASSISTANT_SPACE_TITLE exists for A yet."""


def room_id() -> str | None:
    return db.kv_get("assistant_room_id") or None


def find_space() -> str:
    """Find A's space titled ASSISTANT_SPACE_TITLE and save its id. Raises SpaceNotFound if there isn't one.

    Looked up by title on every start, so renaming or re-creating the space just works. If several
    spaces share the title, the one A created wins.
    """
    my_id = db.kv_get("my_person_id")
    matches = [r for r in wx.list_group_rooms() if (r.get("title") or "").strip() == config.ASSISTANT_SPACE_TITLE]
    if not matches:
        db.kv_set("assistant_room_id", "")
        raise SpaceNotFound(
            f"No Webex space named '{config.ASSISTANT_SPACE_TITLE}'. In Webex, create a space with exactly that "
            "name (only you in it), or change ASSISTANT_SPACE_TITLE in .env, then restart.")
    mine = [r for r in matches if r.get("creatorId") == my_id]
    room = (mine or matches)[0]
    db.kv_set("assistant_room_id", room["id"])
    return room["id"]


def chat_view(row: dict) -> dict:
    return {"id": row["id"], "role": row["role"], "text": row["text"], "source": row["source"],
            "cards": row["cards"], "created": row["created_at"]}


def as_space_message(markdown: str, role: str) -> str:
    """Add the "this is from the assistant" header (templates/chat/space_post.md)."""
    return render("chat/space_post.md", body=markdown, kind="alert" if role == "notice" else "reply",
                  assistant_name=config.ASSISTANT_NAME)


def post(markdown: str, role: str = "assistant", cards: list | None = None, source: str = "system") -> dict:
    """Post from the assistant into the Webex Assistant space and the UI thread. Returns the chat row.

    If Webex is unreachable, the turn is still stored (the UI shows it) and the error is logged.
    """
    row = db.add_chat(role, markdown, source, cards=cards)
    target = room_id()
    if target:
        try:
            message = wx.user_send(as_space_message(markdown, role), target)
            db.set_chat_webex_id(row["id"], message["id"])
        except Exception as exc:
            log(f"[error] posting to the {config.ASSISTANT_SPACE_TITLE} space failed: {exc}")
    events.publish("chat_turn", chat_view(row))
    return row


def mirror_user_text(text: str) -> dict:
    """A typed in the UI: store the turn and copy it into the Webex space as A's own words (no header)."""
    row = db.add_chat("user", text, "ui")
    target = room_id()
    if target:
        try:
            message = wx.user_send(text, target)
            db.set_chat_webex_id(row["id"], message["id"])
        except Exception as exc:
            log(f"[error] mirroring to the {config.ASSISTANT_SPACE_TITLE} space failed: {exc}")
    events.publish("chat_turn", chat_view(row))
    return row
