"""Webex REST calls.

Two identities:
- A (the filtered user): OAuth access token from the kv table, refreshed automatically.
  Used for reading messages/rooms and managing webhooks.
- Priority bot: long-lived PRIORITY_BOT_TOKEN from .env. Used only to send A notifications.
  Never read with the bot token: in group spaces a bot only sees messages that @mention it.

httpx honors HTTPS_PROXY and SSL_CERT_FILE from the environment, which is all the
company network setup needs.

Run `python -m shared.webex_client` to check both identities.
Run `python -m shared.webex_client send-test` to also have the bot message A.
"""

import sys
import time

import httpx

from shared import config
from shared.db import kv_get, kv_set

API = "https://webexapis.com/v1"
SCOPES = "spark:messages_read spark:messages_write spark:rooms_read spark:people_read spark:kms"

# Refresh a bit before the real expiry so a call never starts with an almost-dead token.
REFRESH_MARGIN_SECONDS = 5 * 60


# --- OAuth tokens (A) ---

def _save_tokens(data: dict) -> None:
    now = int(time.time())
    kv_set("access_token", data["access_token"])
    kv_set("access_token_expires_at", str(now + int(data["expires_in"])))
    kv_set("refresh_token", data["refresh_token"])
    kv_set("refresh_token_expires_at", str(now + int(data["refresh_token_expires_in"])))


def _token_request(form: dict) -> None:
    form = {
        "client_id": config.require("WEBEX_CLIENT_ID"),
        "client_secret": config.require("WEBEX_CLIENT_SECRET"),
        **form,
    }
    resp = httpx.post(f"{API}/access_token", data=form, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Token request failed ({resp.status_code}): {resp.text}")
    _save_tokens(resp.json())


def exchange_code(code: str) -> None:
    """Step 4 of the login flow: trade the one-time code for access + refresh tokens."""
    _token_request({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.WEBEX_REDIRECT_URI,
    })


def refresh_access_token() -> None:
    refresh_token = kv_get("refresh_token")
    if not refresh_token:
        raise SystemExit("Not logged in. Run: python -m scripts.login")
    _token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})


def get_token() -> str:
    """A's access token, refreshed first if it expires within REFRESH_MARGIN_SECONDS."""
    token = kv_get("access_token")
    if not token:
        raise SystemExit("Not logged in. Run: python -m scripts.login")
    expires_at = int(kv_get("access_token_expires_at", "0"))
    if expires_at - time.time() < REFRESH_MARGIN_SECONDS:
        refresh_access_token()
        token = kv_get("access_token")
    return token


# --- HTTP helpers ---

def _send(method: str, path: str, token: str, **kwargs) -> httpx.Response:
    resp = httpx.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {token}"},
                         timeout=30, **kwargs)
    if resp.status_code == 429:
        # Rate limited: Webex says how long to wait.
        time.sleep(int(resp.headers.get("Retry-After", "5")))
        resp = httpx.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {token}"},
                             timeout=30, **kwargs)
    return resp


def _result(resp: httpx.Response):
    resp.raise_for_status()
    return resp.json() if resp.content else None


def user_request(method: str, path: str, **kwargs):
    """Call the API as A. On 401 (token revoked or expired early), refresh once and retry."""
    resp = _send(method, path, get_token(), **kwargs)
    if resp.status_code == 401:
        refresh_access_token()
        resp = _send(method, path, get_token(), **kwargs)
    return _result(resp)


def bot_request(method: str, path: str, **kwargs):
    """Call the API as the Priority bot."""
    return _result(_send(method, path, config.require("PRIORITY_BOT_TOKEN"), **kwargs))


# --- A: reading ---

def me() -> dict:
    return user_request("GET", "/people/me")


def get_message(message_id: str) -> dict:
    return user_request("GET", f"/messages/{message_id}")


def get_room(room_id: str) -> dict:
    return user_request("GET", f"/rooms/{room_id}")


def list_rooms(max_items: int = 50) -> list[dict]:
    """Rooms A is in, most recently active first (polling mode starts here)."""
    return user_request("GET", "/rooms", params={"sortBy": "lastactivity", "max": max_items})["items"]


def list_messages(room_id: str, max_items: int = 50) -> list[dict]:
    """Newest messages in a room, newest first."""
    return user_request("GET", "/messages", params={"roomId": room_id, "max": max_items})["items"]


# --- A: webhooks ---

def list_webhooks() -> list[dict]:
    return user_request("GET", "/webhooks")["items"]


def create_webhook(name: str, target_url: str, secret: str,
                   resource: str = "messages", event: str = "created") -> dict:
    return user_request("POST", "/webhooks", json={
        "name": name, "targetUrl": target_url, "resource": resource,
        "event": event, "secret": secret,
    })


def delete_webhook(webhook_id: str) -> None:
    user_request("DELETE", f"/webhooks/{webhook_id}")


# --- Priority bot ---

def bot_me() -> dict:
    return bot_request("GET", "/people/me")


def bot_send(markdown: str, to_person_email: str | None = None, room_id: str | None = None) -> dict:
    """Bot posts a message, either 1:1 to a person (by email) or into a room."""
    body = {"markdown": markdown}
    if room_id:
        body["roomId"] = room_id
    else:
        body["toPersonEmail"] = to_person_email
    return bot_request("POST", "/messages", json=body)


if __name__ == "__main__":
    user = me()
    left = int(kv_get("access_token_expires_at", "0")) - int(time.time())
    print(f"A:   {user['displayName']} <{user['emails'][0]}>  (access token valid for {left // 3600}h)")
    bot = bot_me()
    print(f"Bot: {bot['displayName']} <{bot['emails'][0]}>  (type={bot['type']})")
    if "send-test" in sys.argv:
        bot_send("🔔 Test from **Priority**: the bot can reach you.", to_person_email=user["emails"][0])
        print("Test message sent to A.")
