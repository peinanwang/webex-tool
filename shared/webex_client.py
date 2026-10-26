"""Webex REST calls.

One identity: A (the filtered user). The OAuth access token (from the integration login, stored in
the kv table) is refreshed automatically. It's used for everything: reading messages and rooms,
managing webhooks, and posting into A's Webex Assistant space.

httpx honors HTTPS_PROXY and SSL_CERT_FILE from the environment, which is all the
company network setup needs.

Run `python -m shared.webex_client` to check the login.
"""

import threading
import time

import httpx

from shared import config
from shared.db import add_app_post, kv_get, kv_set

API = "https://webexapis.com/v1"
# Set in .env (WEBEX_SCOPES). Every scope here must also be ticked on the integration page; re-run
# `python -m scripts.login` after changes.
SCOPES = config.WEBEX_SCOPES

# Webex rejects message text over ~7439 bytes; we cut long posts (full text stays in the UI).
MAX_POST_CHARS = 6500

# Held while posting as A and recording the new id in app_posts. The pipeline takes the same lock
# before checking app_posts, so a poll that lands between "posted" and "recorded" can't mistake our
# own post for A typing.
post_lock = threading.Lock()

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


# --- A: reading ---

def me() -> dict:
    return user_request("GET", "/people/me")


def get_message(message_id: str) -> dict:
    return user_request("GET", f"/messages/{message_id}")


def get_person(person_id: str) -> dict:
    return user_request("GET", f"/people/{person_id}")


def get_room(room_id: str) -> dict:
    return user_request("GET", f"/rooms/{room_id}")


def list_rooms(max_items: int = 50) -> list[dict]:
    """Rooms A is in, most recently active first (polling mode starts here)."""
    return user_request("GET", "/rooms", params={"sortBy": "lastactivity", "max": max_items})["items"]


def list_messages(room_id: str, max_items: int = 50) -> list[dict]:
    """Newest messages in a room, newest first."""
    return user_request("GET", "/messages", params={"roomId": room_id, "max": max_items})["items"]


def list_group_rooms(max_items: int = 1000) -> list[dict]:
    return user_request("GET", "/rooms", params={"type": "group", "max": max_items})["items"]


def search_people(name_or_email: str, max_items: int = 5) -> list[dict]:
    """Webex directory lookup by email (exact) or display name (prefix)."""
    key = "email" if "@" in name_or_email else "displayName"
    return user_request("GET", "/people", params={key: name_or_email, "max": max_items})["items"]


# --- A: posting (Webex Assistant space) ---

def user_send(markdown: str, room_id: str) -> dict:
    """Post as A into a room and remember the id, so the pipeline skips it when polling sees it.

    Messages A sends never trigger a notification for A; that's why alerts also use the desktop.
    """
    if len(markdown) > MAX_POST_CHARS:
        markdown = markdown[:MAX_POST_CHARS] + "\n\n_… cut here; the full text is in the Webex Focus UI._"
    with post_lock:
        message = user_request("POST", "/messages", json={"roomId": room_id, "markdown": markdown})
        add_app_post(message["id"])
    return message


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


if __name__ == "__main__":
    user = me()
    left = int(kv_get("access_token_expires_at", "0")) - int(time.time())
    print(f"Logged in as {user['displayName']} <{user['emails'][0]}>  (access token valid for {left // 3600}h)")
