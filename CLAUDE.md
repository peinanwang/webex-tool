# Webex Focus

POC (started at a company hackathon): keep Webex quiet while the user focuses. Every message is triaged into **High priority** (notify now) or **Regular** (held for a summary). The user talks to an **AI assistant** in a private Webex "Focus Assistant" space, or in a local **web UI**, to get summaries, check and change rules, and turn focus mode on and off.

Full phased plan: @docs/PLAN.md. AI tool catalog: `docs/ai-tools.md`. UI design: `docs/ui.md`. Original requirements: `docs/new_requirements.md`.

**Migration status:** the docs describe v2. The code is still v1 (statuses `notify`/`digest`/`ignore`, bot relay, tools in `mcp_server/server.py`) until each v2 phase lands. Check the phase checkboxes in PLAN.md before assuming something exists.

## Project context

- Built and tested on personal free Webex accounts. The demo must also run on the **company network** (no bot, no ngrok, proxy + TLS inspection).
- This repo is the single home for everything: Python app, MCP server, templates, web UI (`ui/`), and docs.
- A non-technical coworker will edit the product's wording, so **all user-facing text lives in `templates/`**.
- The hackathon code lives on the company network and is not available here. This repo implements everything, and the company repo will later be rebased on it. Keep company-specific parts behind the swap points in `docs/architecture.md`.
- LLM: OpenAI API, direct, with an API key. Later the company uses its own OpenAI-compatible gateway, possibly with an older (GPT-4 class) model, so code must work on weaker models (see Conventions).
- Demo machine: **macOS**. Windows desktop notifications should also work.
- Email is **mocked**: summaries are "sent" by writing `.eml` + `.html` to `data/outbox/`. A coworker adds real delivery later.

## How to work with me

I'm new to FastAPI, MCP, webhooks, LLM tool calling, React, and SSE (comfortable with Python and general software engineering). So:

- Before writing code that introduces one of these concepts, explain it in a few sentences: what it is, why we need it here, and how the pieces connect.
- Work in small steps; after each step, tell me how to run and verify it myself.
- Add short comments where FastAPI/MCP/webhook/LLM behavior isn't obvious (e.g., why we re-fetch messages, why we skip our own posts).
- Prefer simple, readable code over clever abstractions — this is a POC I need to understand and demo. No agent frameworks; the tool-calling loop is our own short code.
- When I hit a concept question mid-build, answer it before continuing.

## Architecture (two processes, one SQLite DB)

- `listener/` — the always-on app (FastAPI). Finds new messages (`LISTENER_MODE`: `polling` default, `webhook` for home), and every message goes through one `process_message()`:
  - skip ids in `app_posts` (messages we posted ourselves)
  - A's message in the Focus Assistant space → the agent (`listener/assistant.py`)
  - A's message elsewhere → store as `self`
  - everything else → triage → store → notify if `high` **and** focus is on
  - Also hosts `api.py` (JSON for the UI), `events.py` (SSE), `scheduler.py` (23:59 summary), and serves `ui/dist`.
- `mcp_server/` — MCP over stdio for Claude Code / Copilot. A thin adapter that registers every tool from `shared/tools.py`. Never `print()` there — stdout is the MCP channel.
- `shared/` — `db.py`, `webex_client.py`, `rules.py` (pure), `focus.py`, `notifier.py`, `templates.py`, `tools.py` (the one tool registry), `llm.py` (the only file that imports `openai`), `agent.py`, `summary.py`, `emailer.py` (outbox mock), `desktop_notify.py`, `triage_ai.py`.
- `templates/` — Jinja2 files for every response (`notify/`, `chat/`, `summary/`) and every LLM prompt (`prompts/`), plus `samples.yaml` and a README for non-technical editors.
- `ui/` — React + Vite + TypeScript + Tailwind. Tabs: Assistant, Triage, Rules, Summaries, Templates.
- `scripts/` — `login.py`, `seed_rules.py`, `setup_assistant_space.py`, `eval_triage.py`, `reset_demo.py`.
- `data/focus.db` (SQLite, WAL mode). `docs/` — plan, phases, design notes. `docs/archive/v1/` — superseded v1 phases.

## Stack

Python 3.11+, FastAPI, uvicorn, httpx, official `mcp` SDK **v2** (`from mcp.server.mcpserver import MCPServer` — v1's `FastMCP` was renamed; same `@mcp.tool()` / `@mcp.prompt()` decorators), SQLite, Jinja2 (sandboxed), `openai` SDK (Chat Completions + `tools`; `OPENAI_BASE_URL` configurable), APScheduler, desktop notifications (`terminal-notifier` / `osascript` on macOS, `win11toast` on Windows), stdlib `email` for the outbox. Frontend: React + Vite + TS + Tailwind, SSE for live updates. ngrok only for webhook mode at home.

## Webex facts (don't re-discover these)

- No API can block delivery, suppress a push notification, or mute a space. The user mutes spaces or uses DND in the Webex client.
- **Company network: the Priority bot is blocked**, and ngrok/webhooks can't reach the laptop → polling + integration only.
- **Integration posts are sent as A, and Webex never notifies you about your own messages.** Alerts therefore go to the Focus Assistant space (the record) **plus a desktop notification** (the real alert). The bot channel is optional, for home use.
- Every message we post as A is recorded in `app_posts`. The pipeline skips those ids, otherwise polling would treat our replies as A's chat input (loop).
- Creating the Focus Assistant space needs the `spark:rooms_write` scope (re-login after adding it).
- Webhook payloads contain IDs only → always `GET /v1/messages/{id}` with the user's token for text.
- Webhook registered with A's OAuth token fires for all spaces A is in. Bots only see @mentions in group spaces, so never read with the bot token.
- Messages sent by the Priority bot: skip entirely. Messages sent by A outside the assistant space: store with `category='self'`, `reason='self'` — never triage or notify them; they exist so summaries show both sides.
- No history backfill: the DB only has messages since the listener first started. Polling catches up on restart because cursors persist; webhook mode loses messages while down.
- Personal access tokens expire in ~12h; use integration OAuth + refresh token (stored in `kv`; migrations must keep `kv`).
- Free ngrok URL changes on restart → listener deletes and re-registers its webhook on startup.
- Polling: `GET /v1/rooms?sortBy=lastactivity`, then `GET /v1/messages?roomId=` for rooms active since their cursor (per-room cursor in `kv`, dedupe by id, first run starts at "now"). 500 ms worked at the hackathon; default `POLL_INTERVAL=2`; the client honors `Retry-After` on 429.
- Company network: outbound calls may need `HTTPS_PROXY`; TLS inspection causes `CERTIFICATE_VERIFY_FAILED` → point `SSL_CERT_FILE` at the company CA bundle. This applies to the LLM API too.
- Webhook signature: verify `X-Spark-Signature` (HMAC-SHA1 of body with webhook secret).

## Triage semantics

Categories: `high` | `regular`. Rule match types: sender, space, keyword, mention-of-A, and (Phase 10) `topic` (plain-language, judged by AI).
Order: rules → if none matched, @mention of A → `high` → AI triage (if `AI_TRIAGE=on`) → `regular`.
Precedence among matching rules: **high > regular** (ties → oldest rule). Rules always beat defaults and AI, so a `regular` space rule silences @mentions there unless a `high mention` rule exists (seeded by `scripts/seed_rules.py`). Rule logic lives in `shared/rules.py` (pure, unit-tested).

Message `category`: `high`, `regular`, `self`. Each row also stores `reason` (e.g. `rule#2 sender=…`, `default:mention`, `ai: reports an outage`), `decided_by` (`rule`/`default`/`ai`/`self`), `focus_on`, `notified_at`, and `feedback` (`correct`/`should_be_high`/`should_be_regular`).

## Focus mode

- On: `high` messages notify. Off: nothing notifies, but everything is still triaged and stored.
- Each on→off stretch is a row in `focus_sessions`. Turning focus off generates a `focus_session` summary of the regular messages A missed.

## Summaries

- Any period, all spaces. Scopes: `held` (regular only) = "what I missed"; `all` (everything incl. `high` and `self`) = "what happened".
- Kinds: `on_demand` (A asks), `focus_session` (focus turned off), `end_of_day` (23:59, written to the email outbox; caught up at startup if missed).
- Generated by our LLM as structured JSON, then rendered by `templates/summary/summary.md`. Stored in the `summaries` table.

## Test accounts

A = filtered user (owns the integration + optional Priority bot), B = "important" sender, C = noisy sender.
Spaces: A↔B, A↔C, group A+B+C, and A's private "Focus Assistant" space.

## Conventions

- Secrets only in `.env` (gitignored); `.env.example` committed.
- **No user-facing text in Python or React code.** Notifications, chat replies, summaries, emails, and LLM prompts come from `templates/` (UI labels from `ui/src/copy.ts`). Every template has a header comment listing its placeholders and an entry in `templates/samples.yaml`; `pytest` renders all of them.
- Every tool lives in `shared/tools.py` and returns `{"data": ..., "display": <rendered template>}`. The agent, the MCP server, and the UI API all call these same functions — never duplicate tool logic.
- Deterministic paths first: slash commands and rules must work with no LLM available.
- Weak-model friendly: use Chat Completions + `tools` (no newer OpenAI-only APIs), get structured output via a forced tool call (`llm.extract`), keep tool descriptions short with an example, and no parallel tool calls.
- Desktop notification text is passed to `osascript` as arguments, never pasted into the script (message text is untrusted).
- The UI binds to localhost only (no auth; it shows private messages).
- Work phase by phase; finish each phase's checkpoint before starting the next. Add a dated line to the PLAN.md status log when a phase finishes or a decision changes.
