"""One-time OAuth login as A.

Run it while the listener is NOT running (both use port 8000):

    python -m scripts.login

It opens the Webex consent page, catches the redirect on localhost, stores A's tokens
in the kv table, and records A's personId for the listener.
Run it again any time you change scopes or the refresh token expires (~90 days).

If the browser can't reach the script (redirect page shows "can't connect"), use:

    python -m scripts.login --paste

and paste the full URL from the browser's address bar after clicking Accept.
"""

import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from shared import config
from shared.db import init_db, kv_set
from shared.webex_client import SCOPES, exchange_code, me

AUTHORIZE_URL = "https://webexapis.com/v1/authorize"


class CallbackHandler(BaseHTTPRequestHandler):
    """Handles the single browser redirect: /oauth/callback?code=...&state=..."""

    result: dict = {}

    def do_GET(self):
        url = urlparse(self.path)
        if url.path != urlparse(config.WEBEX_REDIRECT_URI).path:
            self.send_response(404)
            self.end_headers()
            return
        CallbackHandler.result = {k: v[0] for k, v in parse_qs(url.query).items()}
        ok = "code" in CallbackHandler.result
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        message = "Login received. You can close this tab." if ok else "Login failed. Check the terminal."
        self.wfile.write(f"<h2>{message}</h2>".encode())

    def log_message(self, *args):
        pass  # keep the terminal quiet


def main() -> None:
    init_db()
    redirect = urlparse(config.WEBEX_REDIRECT_URI)

    # `state` is a random value we send and expect back, so we know the redirect
    # came from the login we just started (protects against forged callbacks).
    state = secrets.token_urlsafe(16)
    url = AUTHORIZE_URL + "?" + urlencode({
        "client_id": config.require("WEBEX_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": config.WEBEX_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })

    print("Opening the Webex login page. Log in as A, then click Accept on the permissions page.")
    print(f"Asking for: {SCOPES}")
    print(f"If the browser doesn't open, visit:\n{url}\n")

    if "--paste" in sys.argv:
        # Fallback: no local server. After Accept, the browser lands on localhost (and may show
        # "can't connect"), but the address bar still holds the code we need.
        webbrowser.open(url)
        pasted = input("After clicking Accept, paste the full URL from the address bar here:\n> ").strip()
        result = {k: v[0] for k, v in parse_qs(urlparse(pasted).query).items()}
    else:
        server = HTTPServer((redirect.hostname, redirect.port or 80), CallbackHandler)
        webbrowser.open(url)
        print(f"Waiting for the browser to return to {config.WEBEX_REDIRECT_URI} ... (Ctrl+C to cancel)")
        # Serve requests until the callback arrives (ignores stray ones like /favicon.ico).
        while not CallbackHandler.result:
            server.handle_request()
        server.server_close()
        result = CallbackHandler.result

    if not result:
        raise SystemExit("No code found in the pasted URL.")
    if "error" in result:
        hint = ""
        if result["error"] == "invalid_scope":
            hint = (f"\nThis login asked for: {SCOPES}\n"
                    "Every one of these must be ticked on your integration (developer.webex.com → My Webex Apps).\n"
                    "Easiest: tick spark:all there, Save, and put WEBEX_SCOPES=spark:all spark:kms in .env.")
        raise SystemExit(f"Login failed: {result['error']} {result.get('error_description', '')}{hint}")
    if result.get("state") != state:
        raise SystemExit("Login failed: state mismatch (callback didn't come from this login).")

    exchange_code(result["code"])

    user = me()
    kv_set("my_person_id", user["id"])
    kv_set("my_email", user["emails"][0])
    kv_set("my_display_name", user["displayName"])

    print(f"Logged in as {user['displayName']} <{user['emails'][0]}>")
    print("Tokens saved. Next: python -m shared.webex_client")


if __name__ == "__main__":
    main()
