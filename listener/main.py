"""The always-running listener.

    uvicorn listener.main:app --port 8000

LISTENER_MODE in .env picks how new messages arrive:
- webhook: Webex POSTs to /webhook through ngrok (start `ngrok http 8000` first)
- polling: a background loop asks Webex for new messages (no ngrok)
Either way, each message goes through pipeline.process_message().
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from listener import webhook
from listener.pipeline import my_ids, process_message
from listener.poller import poll_forever
from shared import config
from shared.db import init_db


def _process_safely(message_id: str) -> None:
    """Background task wrapper: one bad message shouldn't crash anything, just get logged."""
    try:
        process_message(message_id)
    except Exception as exc:
        print(f"[error] message {message_id}: {exc}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup (before `yield`) and once at shutdown (after it).
    init_db()
    my_ids()  # fail fast with a clear message if login.py hasn't been run
    poll_task = None
    if config.LISTENER_MODE == "webhook":
        target = webhook.register_webhook()
        print(f"Mode: webhook. Registered → {target}", flush=True)
    elif config.LISTENER_MODE == "polling":
        # Remove our webhook so the two modes never run at the same time.
        webhook.delete_our_webhooks()
        poll_task = asyncio.create_task(poll_forever())
        print(f"Mode: polling every {config.POLL_INTERVAL}s (no ngrok needed)", flush=True)
    else:
        raise SystemExit(f"Unknown LISTENER_MODE {config.LISTENER_MODE!r}: use 'webhook' or 'polling'.")
    yield
    if poll_task:
        poll_task.cancel()


app = FastAPI(title="Webex Focus listener", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True, "mode": config.LISTENER_MODE}


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
