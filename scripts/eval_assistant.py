"""Check which tools the AI picks for plain-English requests, against a throwaway copy of the database.

    python -m scripts.eval_assistant
    LLM_MODEL=<a smaller model> python -m scripts.eval_assistant   # mimic the company gateway

Covers every tool in shared/tools.py with the same phrases as docs/VERIFY.md (Appendix A).
Nothing is posted to Webex, your real data isn't changed, and "emails" go to a temp folder.
Cases run in order and share one database, so e.g. "stop watching deploy" follows "watch for the word deploy".
"""

import tempfile
from pathlib import Path

from shared import config, db, llm

# (plain-English request, tools that must be called)
CASES = [
    ("am I in focus mode?", ["get_focus_status"]),
    ("start focusing", ["set_focus_mode"]),
    ("I'm done focusing", ["set_focus_mode"]),
    ("show my rules", ["list_rules"]),
    ("notify me when Bob writes", ["find_contacts", "add_rule"]),
    ("anything in Team Chat can wait", ["add_rule"]),
    ("always notify me when I'm mentioned", ["add_rule"]),
    ("anything with the word urgent is important", ["add_rule"]),
    ("pause the urgent rule", ["set_rule_enabled"]),
    ("turn the urgent rule back on", ["set_rule_enabled"]),
    ("would I get pinged if Carol says 'server down' in Team Chat?", ["test_rule"]),
    ("delete the Team Chat rule", ["delete_rule"]),
    ("what's Carol's email address?", ["find_contacts"]),
    ("which spaces have I been getting messages from?", ["find_spaces"]),
    ("what did Carol say today?", ["search_messages"]),
    ("anything about the release today?", ["search_messages"]),
    ("Carol's last message was actually important", ["search_messages", "mark_message"]),
    ("how accurate was triage today?", ["get_triage_stats"]),
    ("what did I miss?", ["summarize"]),
    ("summarize everything today", ["summarize"]),
    ("show my summaries", ["list_summaries"]),
    ("show summary 1", ["get_summary"]),
    ("email me summary 1", ["email_summary"]),
    ("what am I paying attention to?", ["get_focus_profile"]),
    ("only production outages are urgent for me; questions from teammates can wait", ["set_focus_profile"]),
    ("what do you think is important to me?", ["explain_focus_profile"]),
    ("watch for the word deploy", ["watch"]),
    ("keep me posted on anything about the budget", ["watch"]),
    ("what words am I watching?", ["list_watches"]),
    ("stop watching deploy", ["unwatch"]),
]


def _seed() -> None:
    from shared.timeutil import now_webex_utc
    for i, (email, name, room, text) in enumerate([
        ("bob@example.com", "Bob Chen", "Bob Chen", "can you review my PR?"),
        ("carol@example.com", "Carol Diaz", "Team Chat", "release moved to Friday"),
        ("carol@example.com", "Carol Diaz", "Random", "cake in the kitchen"),
    ]):
        db.insert_message({"id": f"m{i}", "room_id": f"r-{room}", "room_title": room,
                           "room_type": "direct" if room == name else "group", "person_id": f"p{i}",
                           "person_email": email, "person_name": name, "text": text, "created": now_webex_utc(),
                           "mentioned_me": 0, "category": "regular", "reason": "default", "decided_by": "default",
                           "focus_on": 0})
    db.add_summary("on_demand", now_webex_utc(), now_webex_utc(), "held", "## Summary\n**Release moved to Friday.**", None)


def main() -> None:
    if not llm.is_configured():
        raise SystemExit("Set OPENAI_API_KEY in .env first.")
    from shared import agent, summary
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = Path(tmp) / "eval.db"
        config.OUTBOX_DIR = Path(tmp) / "outbox"
        db.init_db()
        _seed()
        summary.summarize_session_in_background = lambda session_id: None  # don't post anything
        passed, original = 0, agent.tools.call
        for request, expected in CASES:
            calls = []
            agent.tools.call = lambda name, args=None: (calls.append(name), original(name, args))[1]
            with db.connect() as conn:  # each case starts a fresh conversation
                conn.execute("DELETE FROM chat_messages")
            db.add_chat("user", request, "ui")
            reply, _ = agent.reply(request)
            if "delete" in request and "Reply **yes**" in reply:  # the confirmation step
                db.add_chat("assistant", reply, "system")
                db.add_chat("user", "yes", "ui")
                agent.reply("yes")
            agent.tools.call = original
            ok = all(name in calls for name in expected)
            passed += ok
            print(f"{'✓' if ok else '✗'} {request!r}: called {calls or 'nothing'}"
                  + ("" if ok else f" (expected {expected})"))
        print(f"\n{passed}/{len(CASES)} passed with {config.LLM_MODEL}")


if __name__ == "__main__":
    main()
