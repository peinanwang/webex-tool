# Phase 2 — OAuth login & Webex client

Get a long-lived way to call the Webex API as A. Personal access tokens expire in about 12h, so we use the integration's OAuth flow and a refresh token.

## Learn first
- **OAuth authorization code flow**: open a Webex URL in the browser, A approves, Webex redirects to our `redirect_uri` with a `code`, and we exchange the code for an access token (~14 days) and a refresh token (~90 days).
- **Refresh**: when the access token expires (or a call returns 401), we trade the refresh token for a new access token. No browser needed.

## Action items
- [x] `scripts/login.py` (run as `python -m scripts.login`; listener must not be running, both use port 8000; `--paste` fallback if the browser can't reach it):
  - [x] Builds the authorize URL (client_id, redirect_uri, scopes, state) and opens it in the browser
  - [x] Runs a tiny local server on `localhost:8000` to catch `/oauth/callback?code=…`
  - [x] Exchanges the code at `POST https://webexapis.com/v1/access_token`
  - [x] Saves `access_token`, `refresh_token`, and their expiry times in the `kv` table
  - [x] Calls `GET /v1/people/me` and saves A's `personId`, email, and name in `kv`
- [x] `shared/webex_client.py` (httpx):
  - [x] `get_token()`: returns a valid access token and refreshes it if it expires soon
  - [x] Retries once on 401 after a refresh; waits and retries once on 429 (rate limit)
  - [x] Helpers: `me()`, `get_message(id)`, `get_room(id)`, `list_webhooks()`, `create_webhook()`, `delete_webhook(id)`
  - [x] Polling helpers: `list_rooms(sort_by="lastactivity", max=…)`, `list_messages(room_id, max=…)`
  - [x] Separate `bot_send(to_person_email or room_id, markdown)` that uses `PRIORITY_BOT_TOKEN`
- [x] Bot sanity check: call `GET /v1/people/me` with the bot token and save the bot's `personId` in `kv` (used to skip its messages and avoid loops)

## Checkpoint
- [x] `python -m scripts.login` opens the browser, you approve, and it prints "Logged in as <A's name>"
- [x] `python -m shared.webex_client` prints A's and the bot's identity
- [x] Force a refresh: `sqlite3 data/focus.db "UPDATE kv SET value='0' WHERE key='access_token_expires_at'"`, then run `python -m shared.webex_client` again. It still works and shows ~336h left (the refresh path works)
- [x] `python -m shared.webex_client send-test` delivers a test message to A's 1:1 with the Priority bot
