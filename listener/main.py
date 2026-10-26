"""The always-running app: listener + assistant + scheduler + UI API + the built UI.

    python -m listener          # recommended (localhost only, quick Ctrl+C)
    uvicorn listener.main:app --port 8000

LISTENER_MODE in .env picks how new messages arrive:
- polling: a background loop asks Webex for new messages (default; no ngrok, works on the company network)
- webhook: Webex POSTs to /webhook through ngrok (start `ngrok http 8000` first; home only)
Either way, each message goes through pipeline.process_message().
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from listener import scheduler, webhook
from listener.api import router as api_router
from listener.pipeline import my_id, process_message
from listener.poller import poll_forever
from shared import config, focus, llm, triage_ai
from shared.assistant_space import SpaceNotFound, find_space
from shared.db import init_db
from shared.log import log


def _process_safely(message_id: str) -> None:
    """Background task wrapper: one bad message shouldn't crash anything, just get logged."""
    try:
        process_message(message_id)
    except Exception as exc:
        log(f"[error] message {message_id}: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup (before `yield`) and once at shutdown (after it).
    migrated = init_db()
    if migrated:
        log(f"Database upgraded: {', '.join(migrated)}")
    my_id()  # fail fast with a clear message if login.py hasn't been run
    try:
        find_space()
        log(f"Assistant space found: '{config.ASSISTANT_SPACE_TITLE}' (chat with the assistant there)")
    except SpaceNotFound as exc:
        log(f"[warn] {exc}\n       Until then, chat works only on the web page, and alerts are desktop-only.")
    except Exception as exc:
        log(f"[error] Couldn't look up the '{config.ASSISTANT_SPACE_TITLE}' space: {exc}")

    poll_task = None
    if config.LISTENER_MODE == "webhook":
        target = webhook.register_webhook()
        log(f"Mode: webhook. Registered → {target}")
    elif config.LISTENER_MODE == "polling":
        # Remove our webhook so the two modes never run at the same time.
        webhook.delete_our_webhooks()
        poll_task = asyncio.create_task(poll_forever())
        log(f"Mode: polling every {config.POLL_INTERVAL}s (no ngrok needed)")
    else:
        raise SystemExit(f"Unknown LISTENER_MODE {config.LISTENER_MODE!r}: use 'webhook' or 'polling'.")

    jobs = scheduler.start()
    log(f"Focus mode: {'ON' if focus.is_on() else 'OFF'} · AI: "
        f"{config.LLM_MODEL if llm.is_configured() else 'not configured (slash commands only)'} · "
        f"AI triage: {'on' if triage_ai.enabled() else 'off'} · alerts: {','.join(config.NOTIFY_CHANNELS)}")
    log(f"UI: {config.UI_URL}" + ("" if config.UI_DIST_DIR.exists() else "  (not built yet: cd ui && npm run build)"))
    yield
    if poll_task:
        poll_task.cancel()
    if jobs:
        jobs.shutdown(wait=False)


app = FastAPI(title="Webex Focus", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health")
def health():
    return {"ok": True, "mode": config.LISTENER_MODE, "focus": focus.is_on()}


@app.post("/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks):
    # Read the raw bytes: the signature is computed over the exact body Webex sent,
    # so we must verify before parsing it as JSON.
    body = await request.body()
    if not webhook.signature_is_valid(body, request.headers.get("X-Spark-Signature")):
        raise HTTPException(status_code=401, detail="bad signature")

    payload = json.loads(body)
    data = payload.get("data", {})
    message_id = data.get("id")
    if payload.get("resource") != "messages" or not message_id:
        return {"ok": True, "ignored": True}

    # Answer Webex right away; fetching and storing the message happens after the response.
    background.add_task(_process_safely, message_id)
    return {"ok": True}


# The built UI (ui/dist) is served at "/". Mounted last so /api, /health, and /webhook win.
if config.UI_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=config.UI_DIST_DIR, html=True), name="ui")
