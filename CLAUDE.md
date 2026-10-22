# Webex Focus

Hackathon POC: keep Webex silent except for messages that match the user's rules. Matching messages are relayed by a "Priority" bot; everything else is logged and summarized later through an MCP server used from Claude Code / VS Code Copilot.

Full phased plan: @docs/PLAN.md

## Project context

- This is a POC for a company hackathon, built and tested on personal free Webex accounts.
- This repo is the single home for everything: Python listener, MCP server, docs, and (later) any UI.
- Build order: Python listener + MCP server first. A web UI is a stretch goal for later — don't scaffold it until asked. When it happens it goes in `ui/`.

## How to work with me

I'm new to FastAPI, MCP, and webhooks (comfortable with Python and general software engineering). So:

- Before writing code that introduces one of these concepts, explain it in a few sentences: what it is, why we need it here, and how the pieces connect.
- Work in small steps; after each step, tell me how to run and verify it myself.
- Add short comments where FastAPI/MCP/webhook behavior isn't obvious (e.g., why we re-fetch messages, why webhooks need a public URL).
- Prefer simple, readable code over clever abstractions — this is a POC I need to understand and demo.
- When I hit a concept question mid-build, answer it before continuing.

## Architecture (two processes, one SQLite DB)

- `listener/` — FastAPI, always running. Gets new messages in one of two modes (`LISTENER_MODE` in `.env`), then runs the same pipeline: fetch full message, apply rules, relay "notify" messages via Priority bot, log everything.
  - `webhook` — Webex POSTs `messages:created` to us through ngrok. Instant; needs a public URL. Default for home/personal setup.
  - `polling` — background loop asks Webex for new messages every `POLL_INTERVAL` seconds (10–15). Outbound HTTPS only — no ngrok, no public URL. For the company network, where tunnels are likely blocked or forbidden.
  - Both modes feed one shared `process_message(id)` function; rules, bot relay, and DB logging must not care which mode delivered the message.
- `mcp_server/` — FastMCP over stdio, launched by the IDE. Rules CRUD, query suppressed messages, digest input/save.
- `shared/` — `db.py`, `webex_client.py` (REST + token refresh), `rules.py`.
- `scripts/login.py` — one-time OAuth code flow, stores refresh token in DB.
- `data/focus.db` (SQLite, WAL mode), `data/digests/YYYY-MM-DD.md`.
- `docs/` — plan and notes.
- `ui/` — reserved for the stretch-goal web UI; empty for now.

## Stack

Python 3.11+, FastAPI, uvicorn, httpx, official `mcp` SDK (FastMCP), SQLite, APScheduler (optional), ngrok (webhook mode only). No frontend in v1.

## Webex facts (don't re-discover these)

- No API can block delivery or suppress a push notification. "Suppression" = user mutes noisy spaces in the Webex client; only the Priority bot's 1:1 space stays unmuted.
- Webhook payloads contain IDs only → always `GET /v1/messages/{id}` with the user's token for text.
- Webhook registered with the user's (A's) OAuth token fires for all spaces A is in. Bots only see @mentions in group spaces, so never use the bot token for reading.
- Messages sent by the Priority bot: skip entirely (avoid loops). Messages sent by A: store with `status='self'`, `reason='self'` — never run rules on them or relay them; they exist only so summaries show both sides of a conversation.
- No history backfill: the DB only has messages since the listener first started. In webhook mode, messages sent while the listener/ngrok is down are lost (Webex doesn't replay). Polling mode catches up on restart because cursors persist.
- Personal access tokens expire in ~12h; use integration OAuth + refresh token.
- Free ngrok URL changes on restart → listener deletes and re-registers its webhook on startup.
- Polling mode: `GET /v1/rooms?sortBy=lastactivity` to find rooms active since the last check, then `GET /v1/messages?roomId=` for each. Keep a per-room cursor (last seen `created`) in the `kv` table; dedupe by message id. On first run, start the cursor at "now" — don't backfill history.
- Company network: ngrok may be blocked or against policy (use polling). Outbound calls may need `HTTPS_PROXY`; TLS inspection causes `CERTIFICATE_VERIFY_FAILED` → point `SSL_CERT_FILE` at the company CA bundle.
- Webhook signature: verify `X-Spark-Signature` (HMAC-SHA1 of body with webhook secret).

## Rules semantics

Actions: `notify` | `digest` | `ignore`. Match on sender, space, keyword, or mention-of-A.
Precedence: ignore > notify > digest. Defaults: @mention of A → notify; unmatched → digest.

Message `status` values: `notify` (relayed), `digest` (held, goes in summary), `ignore` (held, left out of summary by default), `self` (sent by A; context only).

## Summaries

- Summaries cover any period (`start`, `end`; a single day is the common case) across all spaces — 1:1s, group spaces, team channels.
- Two scopes: `held` (default: `digest`, optionally `ignore`) = "what I missed"; `all` = every stored message including `notify` and `self` = "what happened".

## Test accounts

A = filtered user (owns integration + Priority bot), B = "important" sender, C = noisy sender.
Spaces: A↔B, A↔C, group A+B+C.

## Conventions

- Secrets only in `.env` (gitignored); `.env.example` committed.
- Every message row stores `status` and `reason` (which rule fired) — the digest and demo depend on it.
- Keep the digest summarization in the host model (Claude/Copilot); listener needs no LLM key until the optional triage phase.
- Work phase by phase; finish each phase's checkpoint before starting the next.
