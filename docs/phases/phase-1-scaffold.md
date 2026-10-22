# Phase 1 — Project scaffold & database

Set up the repo layout, config, and the SQLite database that both processes share.

## Action items
- [x] Create folders: `listener/`, `mcp_server/`, `shared/`, `scripts/`, `data/digests/`, `ui/` (empty)
- [x] Python virtual env: `python3 -m venv .venv && source .venv/bin/activate`
- [x] `requirements.txt`: `fastapi`, `uvicorn[standard]`, `httpx`, `mcp`, `python-dotenv`, `pytest`
- [x] `.gitignore`: `.venv/`, `.env`, `data/`, `__pycache__/` (created early, at the end of Phase 0)
- [x] `.env.example` (committed) and `.env` (gitignored) with:
  - [x] Rename keys in your own `.env` to match (`BOT_TOKEN`→`PRIORITY_BOT_TOKEN`, `CLIENT_ID`→`WEBEX_CLIENT_ID`, `CLIENT_SECRET`→`WEBEX_CLIENT_SECRET`) and add `WEBHOOK_SECRET`
  - `WEBEX_CLIENT_ID`, `WEBEX_CLIENT_SECRET`, `WEBEX_REDIRECT_URI`
  - `PRIORITY_BOT_TOKEN`
  - `WEBHOOK_SECRET` (any random string; used to verify `X-Spark-Signature`)
  - `LISTENER_MODE=webhook` (`webhook` or `polling`)
  - `PUBLIC_URL` (the ngrok URL; webhook mode only; filled in Phase 3)
  - `POLL_INTERVAL=10` (seconds; polling mode only)
  - `DB_PATH=data/focus.db`
  - Commented-out `HTTPS_PROXY` / `SSL_CERT_FILE` with a note: only needed on the company network
- [x] `shared/config.py`: loads `.env` and exposes settings
- [x] `shared/db.py`: connect with WAL mode, `init_db()` creates tables:
  - `kv` (key, value): OAuth tokens, A's personId, webhook id, bot's personId, polling cursors (`poll_cursor:<roomId>`)
  - `messages` (id, room_id, room_title, room_type, person_id, person_email, text, created, mentioned_me, status, reason, relayed_at)
    - `status`: `notify` | `digest` | `ignore` | `self` (`self` = sent by A, context only)
    - Index on `created` (summaries query by time range)
  - `rules` (id, action, match_type, value, enabled, created_at)
    - `action`: `notify` | `digest` | `ignore`
    - `match_type`: `sender` | `space` | `keyword` | `mention`
- [x] `python -m shared.db` runs `init_db()` so it can be tested on its own

## Learn first
- Why WAL mode: the listener writes while the MCP server reads. WAL lets readers and the writer work at the same time without "database is locked" errors.

## Checkpoint
- [x] `python -m shared.db` creates `data/focus.db`
- [x] `sqlite3 data/focus.db ".tables"` lists `kv messages rules`
- [x] `git status` does not show `.env` or `data/`
