# Phase 0 — Accounts & Webex setup

Manual setup, no code. Do these in the Webex app and on developer.webex.com.

**Status: done (2026-10-21).** The company network questions are still open; they don't block Phase 1.

## Accounts

- [x] A: filtered user (your own name). Owns the integration and the Priority bot.
- [x] B: important sender
- [x] C: noisy sender

## Spaces (in the Webex app)

- [x] As A: start a 1:1 with B
- [x] As A: start a 1:1 with C
- [x] As A: create a group space (e.g. "Team Chat") and add B and C
- [x] Send one "hello" in each space

## Priority bot (as A, developer.webex.com → My Webex Apps → Create a Bot)

- [x] Create a bot named "Priority"
- [x] Copy the **bot access token** (shown only once; it can be regenerated)
- [x] Note the bot's email (e.g. `priority-xxx@webex.bot`)
- [x] As A, send the bot a 1:1 message in the Webex app (creates the space that stays unmuted)

## Integration (as A, developer.webex.com → Create an Integration)

- [x] Redirect URI: `http://localhost:8000/oauth/callback` (must match `scripts/login.py` exactly)
- [x] Scopes checked: `spark:messages_read`, `spark:messages_write`, `spark:rooms_read`, `spark:people_read`
  - `spark:kms` (needed to decrypt message text) isn't in the checkbox list; Webex adds it automatically. It shows up in the generated OAuth Authorization URL, and `login.py` requests it with the other four.
- [x] Copy the **Client ID** and **Client Secret**

## Local tools

- [x] Python 3.11+ (`python3 --version`)
- ngrok is needed for **webhook mode** only. Polling mode doesn't use it.
- [x] ngrok installed (`brew install ngrok`)
- [x] ngrok free account, then `ngrok config add-authtoken <token>` (saved in ngrok's own config, not in `.env`)
- [x] Test it: `ngrok http 8000` shows a public `https://…ngrok-free.app` URL that forwards to localhost
- Inspector at http://127.0.0.1:4040 shows every request through the tunnel (useful for debugging webhooks)

## Company network (ask IT before demo day; doesn't block Phase 1)

- [ ] Are ngrok or other tunnels allowed? (If not, use polling mode there.)
- [ ] Does outbound HTTPS need a proxy? (`HTTPS_PROXY`)
- [ ] Is there TLS inspection? If so, get the company CA bundle (for `SSL_CERT_FILE`)

## Keep safe (these go into `.env`, never commit them)

- Bot token
- Client ID / Client Secret
- `.env` is listed in `.gitignore`

## Checkpoint

- [x] All setup boxes above are checked (the company network items can stay open)
- [x] The three secrets are saved somewhere private
