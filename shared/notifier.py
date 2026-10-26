"""Alert A about a high-priority message (only called when focus mode is on).

NOTIFY_CHANNELS (in .env) lists where alerts go, e.g. `assistant_space,desktop`:
- assistant_space  post in A's Webex Assistant space (the record; doesn't buzz, since it's sent as A)
- desktop          desktop notification (the real alert)

One channel failing doesn't stop the others. All wording comes from templates/notify/.
"""

from shared import config, db, desktop_notify
from shared.assistant_space import post
from shared.log import log
from shared.templates import render
from shared.timeutil import short_local


def template_values(row: dict) -> dict:
    """The placeholders available in templates/notify/* (see samples.yaml)."""
    is_direct = row.get("room_type") == "direct"
    return {
        "sender": row.get("person_name") or row.get("person_email") or "Someone",
        "sender_email": row.get("person_email") or "",
        "space": row.get("room_title") or "",
        "is_direct": is_direct,
        "mentioned_me": bool(row.get("mentioned_me")),
        "text": row.get("text") or "",
        "reason": row.get("reason") or "",
        "time": short_local(row["created"]),
        "link": f"{config.UI_URL}/#/triage?msg={row['id']}",
    }


def message_card(row: dict) -> dict:
    """Structured version of a message for the UI's chat cards."""
    v = template_values(row)
    return {"type": "message", "id": row["id"], "sender": v["sender"], "space": v["space"],
            "is_direct": v["is_direct"], "text": v["text"], "time": v["time"],
            "category": row.get("category"), "reason": v["reason"], "feedback": row.get("feedback")}


def notify(row: dict) -> list[str]:
    """Send the alert on every configured channel. Returns the channels that worked."""
    values = template_values(row)
    delivered = []
    for channel in config.NOTIFY_CHANNELS:
        try:
            if channel == "assistant_space":
                post(render("notify/assistant_post.md", **values), role="notice", cards=[message_card(row)])
            elif channel == "desktop":
                if not desktop_notify.show(render("notify/desktop_title.txt", **values),
                                           render("notify/desktop_body.txt", **values), values["link"]):
                    continue
            else:
                log(f"[warn] unknown notify channel {channel!r} (check NOTIFY_CHANNELS)")
                continue
            delivered.append(channel)
        except Exception as exc:
            log(f"[error] notify via {channel} failed for {row['id']}: {exc}")
    if delivered:
        db.mark_notified(row["id"])
    return delivered
