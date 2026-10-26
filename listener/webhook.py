"""Webhook mode helpers: find the public URL, (re)register the webhook, verify signatures."""

import hashlib
import hmac

import httpx

from shared import config
from shared import webex_client as wx

WEBHOOK_NAME = "webex-focus"


def public_url() -> str:
    """PUBLIC_URL from .env, or else ask the local ngrok agent which URL it's forwarding.

    The free ngrok URL changes on every restart; auto-detecting it saves editing .env each time.
    """
    if config.PUBLIC_URL:
        return config.PUBLIC_URL.rstrip("/")
    try:
        tunnels = httpx.get("http://127.0.0.1:4040/api/tunnels", timeout=3).json()["tunnels"]
    except httpx.HTTPError:
        raise SystemExit("No PUBLIC_URL in .env and ngrok isn't running. Start it: ngrok http 8000")
    https = [t["public_url"] for t in tunnels if t["public_url"].startswith("https://")]
    if not https:
        raise SystemExit("ngrok is running but has no https tunnel. Start it: ngrok http 8000")
    return https[0]


def delete_our_webhooks() -> None:
    """Remove webhooks from previous runs (their ngrok URL is probably dead now)."""
    for hook in wx.list_webhooks():
        if hook["name"] == WEBHOOK_NAME:
            wx.delete_webhook(hook["id"])


def register_webhook() -> str:
    target = f"{public_url()}/webhook"
    delete_our_webhooks()
    wx.create_webhook(WEBHOOK_NAME, target, secret=config.require("WEBHOOK_SECRET"))
    return target


def signature_is_valid(body: bytes, signature: str | None) -> bool:
    """Webex signs the raw request body with our secret: X-Spark-Signature = HMAC-SHA1(secret, body).

    We recompute it and compare. compare_digest takes the same time whether the first or last
    character differs, so an attacker can't guess the signature one character at a time.
    """
    if not signature:
        return False
    expected = hmac.new(config.require("WEBHOOK_SECRET").encode(), body, hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, signature)
