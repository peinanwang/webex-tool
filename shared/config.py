"""Settings loaded from .env, in one place.

Import values from here instead of reading os.environ elsewhere.
Missing secrets are not an error at import time, because not every process needs every secret
(the MCP server never uses the bot token). Call require() where a value is actually needed.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the folder that contains shared/. Resolving paths from here means
# scripts work no matter which directory you run them from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

WEBEX_CLIENT_ID = os.getenv("WEBEX_CLIENT_ID", "")
WEBEX_CLIENT_SECRET = os.getenv("WEBEX_CLIENT_SECRET", "")
WEBEX_REDIRECT_URI = os.getenv("WEBEX_REDIRECT_URI", "http://localhost:8000/oauth/callback")

PRIORITY_BOT_TOKEN = os.getenv("PRIORITY_BOT_TOKEN", "")

LISTENER_MODE = os.getenv("LISTENER_MODE", "webhook")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

DB_PATH = PROJECT_ROOT / os.getenv("DB_PATH", "data/focus.db")
DIGESTS_DIR = PROJECT_ROOT / "data" / "digests"


def require(name: str) -> str:
    """Return a setting's value, or stop with a clear message if it's empty."""
    value = globals().get(name)
    if not value:
        raise SystemExit(f"Missing setting {name}. Add it to .env (see .env.example).")
    return value
