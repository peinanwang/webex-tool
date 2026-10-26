"""Reset to a clean demo state: no rules, nothing stored, focus off.

    python -m scripts.reset_demo
    python -m scripts.reset_demo --clear-outbox     # also delete the mocked emails

Clears messages, chat history, summaries, focus sessions, and **all rules**; turns focus off; resets
the focus profile to the default. Keeps your login and the Webex Assistant space. Stop the listener
first.

With no rules, triage uses its defaults: an @mention of you is High, and everything else is decided
by AI triage (or is Regular if AI triage is off). Rules are then created by chatting with the
assistant ("notify me when Bob writes"), or on the web page's Rules tab.
(`python -m scripts.seed_rules` still exists if you ever want a quick starter set.)
"""

import argparse
import shutil

from shared import config, db, triage_ai
from shared.timeutil import now_webex_utc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clear-outbox", action="store_true", help="also delete the mocked emails")
    args = parser.parse_args()

    db.init_db()
    db.clear_activity()
    db.delete_all_rules(restart_numbering=True)  # messages are gone, so the next rule can be #1 again
    db.kv_set("focus_mode", "off")
    db.kv_set("focus_session_id", "")
    # Start polling from now, so messages sent before the reset aren't imported again.
    db.kv_delete_prefix("poll_cursor:")
    db.kv_set("poll_started_at", now_webex_utc())
    triage_ai.set_profile(triage_ai.DEFAULT_PROFILE)

    if args.clear_outbox and config.OUTBOX_DIR.exists():
        shutil.rmtree(config.OUTBOX_DIR)

    print("Reset done. Focus is OFF. Rules: none.")
    print("With no rules: @mentions of you are High; everything else is decided by AI triage "
          f"({'on' if triage_ai.enabled() else 'off: no OpenAI key or AI_TRIAGE=off, so Regular'}).")
    print("Create rules by chatting in the Webex Assistant space, e.g. \"notify me when Bob writes\".")


if __name__ == "__main__":
    main()
