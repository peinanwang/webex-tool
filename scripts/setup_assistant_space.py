"""Check that Webex Focus can find your assistant space (the listener also does this at startup).

    python -m scripts.setup_assistant_space            # find it
    python -m scripts.setup_assistant_space --hello    # find it and post the /help text there

First create the space yourself in Webex: a space with only you in it, titled exactly like
ASSISTANT_SPACE_TITLE in .env (default "Webex Assistant").
"""

import sys

from shared import config, llm
from shared.assistant_space import SpaceNotFound, find_space, post
from shared.db import init_db
from shared.templates import render

if __name__ == "__main__":
    init_db()
    try:
        room = find_space()
    except SpaceNotFound as exc:
        raise SystemExit(str(exc))
    print(f"Found the '{config.ASSISTANT_SPACE_TITLE}' space: {room}")
    if "--hello" in sys.argv:
        post(render("chat/help.md", llm_ready=llm.is_configured()), role="assistant")
        print("Posted the help text into the space.")
