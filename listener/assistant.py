"""A typed something to the assistant (in the Webex Assistant space, or in the UI).

The pipeline hands us A's message; we store the turn, then compute the reply in a worker thread so
a slow LLM call (several seconds) never pauses polling, and post the reply to both windows.
"""

import threading

from shared import agent, db, events
from shared.assistant_space import chat_view, post
from shared.log import log
from shared.templates import render


def on_user_message(msg: dict) -> None:
    """A wrote in the Webex Assistant space (Webex)."""
    text = (msg.get("text") or "").strip()
    if not text:
        return
    row = db.add_chat("user", text, "webex", webex_message_id=msg["id"])
    events.publish("chat_turn", chat_view(row))
    start_reply(text)


def start_reply(text: str) -> None:
    events.publish("assistant_thinking", {})
    threading.Thread(target=_reply, args=(text,), daemon=True, name="assistant-reply").start()


def _reply(text: str) -> None:
    try:
        markdown, cards = agent.reply(text)
    except Exception as exc:  # agent.reply shouldn't raise, but never leave A without an answer
        log(f"[error] assistant reply failed: {exc!r}")
        markdown, cards = render("chat/error.md", message=str(exc)), []
    post(markdown, role="assistant", cards=cards)
