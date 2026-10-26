"""Try the web page with fake people and messages: no Webex, your real data untouched.

    python -m scripts.ui_sandbox            # → http://localhost:8765 (Ctrl+C to stop; everything is thrown away)

In a second terminal, make new messages "arrive" (they go through the real triage, alerts, and live updates):

    python -m scripts.ui_sandbox say bob "can you review my PR?"                 # 1:1 from Bob
    python -m scripts.ui_sandbox say carol "lunch anyone?" --space Team          # in the Team space
    python -m scripts.ui_sandbox say carol "can you check the build?" --space Team --mention
    python -m scripts.ui_sandbox say carol "prod is down for EU customers!"      # AI triage decides (needs a key)

What's real: the web page, the API, rules, triage (incl. AI triage if OPENAI_API_KEY is set), the
assistant chat (AI if a key is set, quick commands always), summaries, the email outbox, and templates.
What's fake: Webex. Nothing is read from or posted to Webex. The database, outbox, and a *copy* of
templates/ live in a temp folder, so edits on the Templates page don't touch the real files.
Desktop notifications are off.
"""

import argparse
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

PORT = 8765
PEOPLE = {
    "bob": ("Bob Chen", "bob@example.com"),
    "carol": ("Carol Diaz", "carol@example.com"),
    "dana": ("Dana Lee", "dana@example.com"),
}


def say(args) -> None:
    """Send one fake incoming message to the running sandbox."""
    import httpx
    body = {"sender": args.sender.lower(), "text": args.text, "space": args.space or "", "mention": args.mention}
    try:
        resp = httpx.post(f"http://127.0.0.1:{PORT}/sandbox/incoming", json=body, timeout=30)
    except httpx.ConnectError:
        raise SystemExit("The sandbox isn't running. Start it first: python -m scripts.ui_sandbox")
    print(resp.json() if resp.status_code == 200 else f"Error {resp.status_code}: {resp.text}")


def serve() -> None:
    root = Path(__file__).resolve().parent.parent
    tmp = Path(tempfile.mkdtemp(prefix="webex-focus-sandbox-"))
    shutil.copytree(root / "templates", tmp / "templates", ignore=shutil.ignore_patterns("_defaults"))
    # Must be set before any shared.* import, because shared/config.py reads them once.
    os.environ.update(DB_PATH=str(tmp / "sandbox.db"), OUTBOX_DIR=str(tmp / "outbox"),
                      TEMPLATES_DIR=str(tmp / "templates"), DESKTOP_NOTIFIER="off",
                      UI_URL=f"http://localhost:{PORT}", LISTENER_MODE="polling", EOD_ENABLED="off")
    sys.path.insert(0, str(root))

    from contextlib import asynccontextmanager

    import uvicorn
    from fastapi import HTTPException
    from pydantic import BaseModel

    import listener.main as main
    from listener import pipeline
    from shared import db, focus, llm, summary, tools, triage_ai
    from shared import webex_client as wx
    from shared.timeutil import now_webex_utc

    # No Webex: any call that would reach it fails with a normal error (tools handle that).
    def no_webex(*_args, **_kwargs):
        raise RuntimeError("sandbox: Webex is not connected")
    wx.user_request = no_webex

    _seed(db, focus, summary, tools, pipeline)

    class Incoming(BaseModel):
        sender: str
        text: str
        space: str = ""
        mention: bool = False

    def incoming(body: Incoming):
        """Make a fake message arrive, through the real pipeline (triage, alerts, live updates)."""
        if body.sender not in PEOPLE:
            raise HTTPException(400, f"sender must be one of {', '.join(PEOPLE)}")
        name, email = PEOPLE[body.sender]
        room = f"room-{body.space or body.sender}"
        pipeline._room_cache[room] = {"title": body.space or name, "type": "group" if body.space else "direct"}
        msg = {"id": f"sandbox-{uuid.uuid4().hex[:10]}", "roomId": room, "roomType": "group" if body.space else "direct",
               "personId": f"p-{body.sender}", "personEmail": email, "text": body.text, "created": now_webex_utc(),
               "mentionedPeople": ["A"] if body.mention else []}
        outcome = pipeline.process_message(msg["id"], msg)
        row = db.get_message(msg["id"])
        return {"outcome": outcome, "reason": row["reason"] if row else None}

    main.app.add_api_route("/sandbox/incoming", incoming, methods=["POST"])
    main.app.router.routes.insert(0, main.app.router.routes.pop())  # before the "/" static mount

    @asynccontextmanager
    async def no_lifespan(app):  # replaces the real startup: no login check, no polling, no scheduler
        yield
    main.app.router.lifespan_context = no_lifespan

    print(f"\n  Webex Focus UI sandbox → http://localhost:{PORT}", flush=True)
    print(f"  Fake data in {tmp} (deleted on exit). AI: {'on' if llm.is_configured() else 'off (quick commands only)'}"
          f" · AI triage: {'on' if triage_ai.enabled() else 'off'}", flush=True)
    print('  New message:  python -m scripts.ui_sandbox say carol "lunch anyone?" --space Team\n', flush=True)
    try:
        uvicorn.run(main.app, host="127.0.0.1", port=PORT, timeout_graceful_shutdown=1, log_level="warning")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _seed(db, focus, summary, tools, pipeline) -> None:
    """A small, believable day: three people, a group space, a few rules, chat history, one summary."""
    from datetime import datetime, timedelta, timezone

    from shared.timeutil import to_webex_utc
    db.init_db()
    db.kv_set("my_person_id", "A")
    db.kv_set("my_display_name", "You (sandbox)")
    db.kv_set("my_email", "you@example.com")
    for key, (name, _email) in PEOPLE.items():
        pipeline._name_cache[f"p-{key}"] = name

    db.add_rule("high", "sender", "bob@example.com")
    db.add_rule("high", "mention")
    db.add_rule("regular", "space", "Random")
    tools.call("watch", {"text": "outage"})

    now = datetime.now(timezone.utc)
    seed = [  # (minutes ago, sender, space, text, category, reason, decided_by, mention)
        (95, "bob", "", "Morning! Can you review my PR before lunch?", "high", "rule#1 sender=bob@example.com", "rule", 0),
        (80, "carol", "Team", "anyone up for coffee?", "regular", "ai: casual social chat", "ai", 0),
        (60, "carol", "Team", "@You can you check why the build is red?", "high", "rule#2 mention", "rule", 1),
        (45, "dana", "Random", "cake in the kitchen 🎂", "regular", "rule#3 space=Random", "rule", 0),
        (30, "carol", "", "small outage on staging, looking into it", "high", "rule#4 keyword=outage", "rule", 0),
        (15, "dana", "", "the slide deck is ready for review", "regular", "ai: shares a finished deliverable", "ai", 0),
    ]
    for i, (mins, who, space, text, category, reason, decided_by, mention) in enumerate(seed):
        name, email = PEOPLE[who]
        room = f"room-{space or who}"
        pipeline._room_cache[room] = {"title": space or name, "type": "group" if space else "direct"}
        db.insert_message({"id": f"seed-{i}", "room_id": room, "room_title": space or name,
                           "room_type": "group" if space else "direct", "person_id": f"p-{who}", "person_email": email,
                           "person_name": name, "text": text, "created": to_webex_utc(now - timedelta(minutes=mins)),
                           "mentioned_me": mention, "category": category, "reason": reason, "decided_by": decided_by,
                           "focus_on": 1})
    db.set_feedback("seed-1", "correct")

    focus.turn_on()
    db.add_chat("user", "show my rules", "webex")
    out = tools.call("list_rules")
    db.add_chat("assistant", out["display"], "system", cards=out["cards"][:3])
    summary.generate(now - timedelta(hours=2), now, "all", "on_demand")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")
    s = sub.add_parser("say", help="make a fake message arrive in the running sandbox")
    s.add_argument("sender", help=f"one of: {', '.join(PEOPLE)}")
    s.add_argument("text")
    s.add_argument("--space", help="group space title (default: a 1:1 chat with the sender)")
    s.add_argument("--mention", action="store_true", help="the message @mentions you")
    args = parser.parse_args()
    say(args) if args.command == "say" else serve()


if __name__ == "__main__":
    main()
