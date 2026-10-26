"""Settings loaded from .env, in one place.

Import values from here instead of reading os.environ elsewhere.
Missing secrets are not an error at import time, because not every process needs every secret
(e.g. the MCP server never logs in itself). Call require() where a value is actually needed.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the folder that contains shared/. Resolving paths from here means
# scripts work no matter which directory you run them from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

# The openai library reads OPENAI_BASE_URL / OPENAI_ORG_ID / OPENAI_PROJECT_ID from the environment by
# itself, and treats a blank value as real (a blank base URL breaks every request). .env.example has
# these lines blank on purpose, so remove blank ones before the library can see them.
for _name in ("OPENAI_BASE_URL", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID"):
    if not os.environ.get(_name, "").strip():
        os.environ.pop(_name, None)


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "on", "true", "yes")


# --- Webex ---
WEBEX_CLIENT_ID = os.getenv("WEBEX_CLIENT_ID", "")
WEBEX_CLIENT_SECRET = os.getenv("WEBEX_CLIENT_SECRET", "")
WEBEX_REDIRECT_URI = os.getenv("WEBEX_REDIRECT_URI", "http://localhost:8000/oauth/callback")
# Permissions the login asks for. They must all be ticked on the integration page, or Webex answers
# "invalid_scope". (Or tick spark:all on the integration and set WEBEX_SCOPES=spark:all spark:kms.)
WEBEX_SCOPES = " ".join((os.getenv("WEBEX_SCOPES", "").strip() or
                         "spark:messages_read spark:messages_write spark:rooms_read "
                         "spark:people_read spark:kms").replace(",", " ").split())


# --- Listener ---
LISTENER_MODE = os.getenv("LISTENER_MODE", "polling")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
# Seconds between polls; decimals are fine (0.5 worked at the hackathon; watch for HTTP 429).
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))
PORT = int(os.getenv("PORT", "8000"))

# --- Alerts ---
# The space A created in Webex to chat with the assistant (exact title), and the name shown on the
# assistant's posts there (templates/chat/space_post.md).
ASSISTANT_SPACE_TITLE = os.getenv("ASSISTANT_SPACE_TITLE", "").strip() or "Webex Assistant"
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "").strip() or "Webex Assistant"
NOTIFY_CHANNELS = [c.strip() for c in os.getenv("NOTIFY_CHANNELS", "assistant_space,desktop").split(",") if c.strip()]
DESKTOP_NOTIFIER = os.getenv("DESKTOP_NOTIFIER", "auto")
UI_URL = os.getenv("UI_URL", f"http://localhost:{PORT}").rstrip("/")

# --- LLM (OpenAI; later the company's OpenAI-compatible gateway via OPENAI_BASE_URL) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID", "")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "5"))
AGENT_HISTORY_TURNS = int(os.getenv("AGENT_HISTORY_TURNS", "20"))

# --- AI triage (messages no rule matched) ---
AI_TRIAGE = _flag("AI_TRIAGE", "on")
TRIAGE_MODEL = os.getenv("TRIAGE_MODEL", "") or LLM_MODEL
TRIAGE_TIMEOUT = float(os.getenv("TRIAGE_TIMEOUT", "8"))

# --- Summaries & email (email is mocked: written to OUTBOX_DIR) ---
EOD_ENABLED = _flag("EOD_ENABLED", "on")
EOD_TIME = os.getenv("EOD_TIME", "23:59")
EOD_SCOPE = os.getenv("EOD_SCOPE", "all")
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "outbox")
EMAIL_TO = os.getenv("EMAIL_TO", "")          # empty = A's Webex email
EMAIL_FROM = os.getenv("EMAIL_FROM", "webex-focus@localhost")

# --- Storage ---
DB_PATH = PROJECT_ROOT / os.getenv("DB_PATH", "data/focus.db")
DIGESTS_DIR = PROJECT_ROOT / "data" / "digests"
OUTBOX_DIR = PROJECT_ROOT / os.getenv("OUTBOX_DIR", "data/outbox")
# Overridable so the UI sandbox (scripts/ui_sandbox.py) can edit a throwaway copy.
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "").strip() or PROJECT_ROOT / "templates")
UI_DIST_DIR = PROJECT_ROOT / "ui" / "dist"


def require(name: str) -> str:
    """Return a setting's value, or stop with a clear message if it's empty."""
    value = globals().get(name)
    if not value:
        raise SystemExit(f"Missing setting {name}. Add it to .env (see .env.example).")
    return value
