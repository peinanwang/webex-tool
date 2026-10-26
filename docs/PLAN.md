# Webex Focus — Roadmap (v2: AI assistant + live triage + web UI)

Goal: keep Webex quiet while A focuses. Every new message is sorted into **High priority** (A gets notified now) or **Regular** (held for a summary). A talks to an **AI assistant** in a private Webex space (or in the web UI) to ask for summaries, check and change rules, and turn focus mode on and off. A **web UI** lets A review the triage results, manage rules, read past summaries, and lets non-technical teammates edit the wording of every response.

Why v2: the hackathon on the company network showed that the bot is blocked, webhooks can't reach a laptop, and the integration does not trigger notifications. The requirements are in [new_requirements.md](new_requirements.md). v1 phase docs are archived in [archive/v1/](archive/v1/).

Work one phase at a time. A phase is done only when its **checkpoint** passes. Each phase has a detail file in [`phases/`](phases/).

**Status (2026-10-26):** Phases 3–11 are built and covered by automated tests (`pytest`). Phases marked [x] are code-complete; their hands-on checks with real Webex accounts are in **[VERIFY.md](VERIFY.md)**.

## The big picture

- **AI tools**: what the assistant can do. See [ai-tools.md](ai-tools.md).
- **Web UI**: tabs, wireframes, and why each one exists. See [ui.md](ui.md).
- **Architecture**: processes, data, and message flow. See [architecture.md](architecture.md).
- **Templates**: every message the product sends is a file in `templates/` that a non-technical teammate can edit. See [Phase 4](phases/phase-4-templates-relay.md).

## What changes from v1

| Area | v1 (before hackathon) | v2 |
|---|---|---|
| Categories | `notify` / `digest` / `ignore` / `self` | **`high`** / **`regular`** / `self` |
| Getting messages | Webhook (ngrok) by default | **Polling by default** (company network); webhook stays for home |
| Alerting A | Priority bot 1:1 | **Integration posts into A's "Webex Assistant" space + desktop notification** (macOS first, Windows supported); bot optional at home |
| Focus mode | Always on | **On/off switch**; turning it off produces a "what you missed" summary |
| AI | Only through Claude Code / Copilot (MCP) | **In-app agent** (OpenAI API; base URL configurable for the company gateway) chatting in the Webex space and the UI; MCP kept as a dev/test bench |
| Tools | Defined inside `mcp_server/server.py` | **One tool registry in `shared/tools.py`**, used by both the agent and MCP |
| Summaries | Written to `data/digests/*.md` by the host model | Stored in the DB; **on demand, when focus turns off, and at 23:59** ("emailed" = written to `data/outbox/` for now) |
| Wording | Hard-coded strings | **Templates** (`templates/`), including the LLM prompts |
| UI | Stretch goal | **Core**: Assistant · Triage · Rules · Summaries · Templates |
| Triage | Rules only | Rules first, then **optional AI triage** for messages no rule matched, improved by A's feedback |

## Phases

- [x] **Phase 0 — Accounts & Webex setup** → [details](phases/phase-0-setup.md)
- [x] **Phase 1 — Project scaffold & database** → [details](phases/phase-1-scaffold.md)
- [x] **Phase 2 — OAuth login & Webex client** → [details](phases/phase-2-oauth.md)
- [x] **Phase 3 — Two categories & focus mode** → [details](phases/phase-3-categories-focus.md)
  Checkpoint: with focus on, B's message is `high` and triggers a notification and C's is `regular`. With focus off, nothing notifies, but every message is still stored and categorized.
- [x] **Phase 4 — Templates & relay through the integration** → [details](phases/phase-4-templates-relay.md)
  Checkpoint: on the company network (no bot, no ngrok), B's message shows a desktop notification and a post in the "Webex Assistant" space. Editing the template changes the next notification without a restart.
- [x] **Phase 5 — One tool registry (shared by MCP and the agent)** → [details](phases/phase-5-tools.md)
  Checkpoint: every tool in [ai-tools.md](ai-tools.md) works from Claude Code via MCP, and `pytest` covers each one.
- [x] **Phase 6 — AI assistant in the Webex space** → [details](phases/phase-6-assistant.md)
  Checkpoint: in the Webex Assistant space, "notify me when Bob writes", "what are my rules?", "turn focus off", and "what did C say today?" all work with OpenAI. `/focus off` works even with no LLM key.
- [x] **Phase 7 — Summaries: on demand, focus-off, end of day + email outbox** → [details](phases/phase-7-summaries.md)
  Checkpoint: "summarize today" works in chat, turning focus off posts a summary of the session, and the end-of-day summary lands in `data/outbox/` as an email preview (`.html` + `.eml`), including catch-up after the laptop was asleep.
- [x] **Phase 8 — Web UI, part 1: shell, Triage, Rules** → [details](phases/phase-8-ui-triage-rules.md)
  Checkpoint: in the UI, A toggles focus, reviews today's messages, marks one as wrongly categorized, and adds a rule with an "affects N of today's messages" preview.
- [x] **Phase 9 — Web UI, part 2: Assistant chat & Summaries (live)** → [details](phases/phase-9-ui-chat-summaries.md)
  Checkpoint: the UI chat and the Webex space show the same conversation within about a second of each other, new messages appear in Triage live, and summaries can be read, regenerated, and "emailed" (to the outbox) from the UI.
- [x] **Phase 10 — AI live triage** → [details](phases/phase-10-ai-triage.md)
  Checkpoint: with no matching rule, "prod is down" becomes `high` with an AI reason and "lunch?" becomes `regular`. `scripts/eval_triage.py` reports accuracy against A's feedback.
- [x] **Phase 11 — Template editor for non-technical teammates** → [details](phases/phase-11-template-editor.md)
  Checkpoint: a teammate edits a template in the UI, previews it with sample data, and saves it. A broken placeholder gets a friendly error and is not saved.
- [ ] **Phase 12 — Demo polish** (README, DEMO.md, reset script done; dry runs pending) → [details](phases/phase-12-demo.md)
  Checkpoint: the demo script runs end to end on the company network in under 7 minutes, twice in a row.

Phases 3–7 make the product work end to end in Webex alone. Phases 8–11 add the UI and the smarter triage. If time runs short, you can demo after Phase 7, or after Phase 9 with the UI.

## Key decisions (v2)

- **Two categories.** `high` (notify now) and `regular` (hold for the summary). `self` stays for A's own messages (context only). `ignore` is gone.
- **Precedence: high > regular.** Missing an important message costs more than one extra ping. Ties go to the oldest rule. When no rule matches: an @mention of A is high. Otherwise AI triage decides (Phase 10, if on), or the message is regular.
- **Focus off = no notifications, but still log and categorize everything.** Summaries and the Triage tab need the full record.
- **One conversation, two windows.** The Webex "Webex Assistant" space and the UI's Assistant tab are the same thread, mirrored both ways.
- **Deterministic first, LLM second.** Slash commands (`/focus off`, `/rules`, `/summary`, `/help`) never need the LLM, so the demo survives an LLM outage. Rules always run before AI triage.
- **Templates for every response.** Python code never contains user-facing text. Tool results are rendered with a template. The LLM's free-form answers pass through a wrapper template. Summaries are LLM-written JSON rendered by a template, so the layout belongs to the template, not the model.
- **OpenAI, through one small adapter.** `shared/llm.py` is the only file that talks to the LLM. It uses the OpenAI SDK's Chat Completions API with `tools`, the most widely supported shape, so the company's OpenAI-compatible gateway can be plugged in later by setting `OPENAI_BASE_URL`. No agent framework, so the loop stays readable.
- **Built to work on a weaker model.** The company gateway may only offer an older model (e.g. GPT-4 class). So: short, concrete tool descriptions; structured output through a forced tool call instead of newer JSON-schema features; slash commands for the critical actions; and every AI phase is also tested with a smaller model.
- **Email is mocked.** `shared/emailer.py` has one `send(...)` function. The only backend for now is the **outbox**: an `.html` preview and an `.eml` file (it opens in Apple Mail like a real email) in `data/outbox/`. A coworker adds SMTP or Microsoft Graph later behind the same function.
- **Desktop notifications: macOS first.** The built-in `osascript` (`DESKTOP_NOTIFIER=osascript`; recent macOS blocks terminal-notifier). Windows uses `win11toast`.
- **UI stack.** React + Vite + TypeScript + Tailwind in `ui/`, served by the same FastAPI process. Live updates use Server-Sent Events. (A simpler alternative is HTMX with server-rendered pages, but a chat UI that should look like Webex is easier in React.)
- **The UI listens on localhost only.** It shows private messages and has no login.

## Answered questions (2026-10-25)

- **Hackathon code**: it lives on the company network and can't be copied here. This repo implements everything from scratch. The hackathon repo will later be rebased on this one, so the company-specific parts sit behind small swap points (see [architecture.md](architecture.md#swap-points-for-the-company-repo)).
- **OS**: the demo runs on macOS. Windows notifications are supported but secondary.
- **Email**: mocked. Summaries are written to `data/outbox/` from the email templates. A coworker implements real delivery later.
- **LLM**: the company uses its own gateway (possibly an older model). That comes later. This repo connects directly to the OpenAI API with an API key.

## Still open

- Polling every 500 ms worked at the hackathon. Watch for HTTP 429 (rate limit) responses over a full day. The default is 2 s and it is configurable.

## Stretch goals (only after Phase 12)

- [ ] Rule suggestions from feedback ("you marked 4 messages from Dana as High; make that a rule?")
- [ ] Draft replies from the assistant (A reviews them, then sends them in Webex)
- [ ] Automatic focus during calendar meetings (Outlook / Webex Meetings)
- [ ] Use Webex's hosted Messaging MCP alongside ours; see [webex-mcp-analysis.md](webex-mcp-analysis.md)
- [ ] Login on the UI so it can be shared beyond localhost
- [ ] Claude API adapter in `shared/llm.py` (`LLM_PROVIDER=anthropic`)

## Handoff items (for the company repo, not this one)

- [ ] Point `OPENAI_BASE_URL` / `OPENAI_API_KEY` at the company LLM gateway and re-run the AI checkpoints on its model
- [ ] Real email delivery (SMTP or Microsoft Graph) behind `shared/emailer.send()`

## Status log

Add a dated line each time a phase is finished or a decision changes.

- 2026-10-21 — Project started. Accounts A, B, C registered.
- 2026-10-21 — Polling moved from stretch goal into Phase 3 as a second listener mode, so the demo can run on the company network without ngrok.
- 2026-10-21 — Summaries support custom periods and two scopes (`held` / `all`). A's own messages are now stored as `status='self'` (never relayed) so "all" summaries show both sides of conversations.
- 2026-10-21 — Decided to build our own MCP server instead of using Webex's hosted MCP; see [webex-mcp-analysis.md](webex-mcp-analysis.md).
- 2026-10-21 — Phase 0 done: accounts, spaces, Priority bot, integration, ngrok. Company network questions for IT still open.
- 2026-10-21 — Phase 1 done: scaffold, config, SQLite (WAL) with kv/messages/rules.
- 2026-10-21 — Phase 2 done: OAuth login (with `--paste` fallback), auto token refresh, Webex client helpers, bot test message delivered.
- 2026-10-22 — Built Phase 3 polling mode and Phases 4–6 (rules engine + relay, MCP server, digest). Unit tests and tool checks pass; checkpoints with real messages are in [archive/v1/VERIFY.md](archive/v1/VERIFY.md). Decision: rules always beat defaults; `notify mention` is seeded as an explicit rule.
- 2026-10-25 — Hackathon learnings: bot blocked on company network, no ngrok, integration posts don't notify → relay through integration + desktop notification, polling (500 ms worked). Coworker prototyped an LLM chat in the integration space.
- 2026-10-25 — **v2 plan.** Two categories (high/regular), focus mode on/off, in-app AI agent (OpenAI or Claude) sharing one tool registry with MCP, templates for all responses, summaries on demand / focus-off / 23:59 email, web UI promoted to core. Old Phases 3–7 archived; new Phases 3–12 defined.
- 2026-10-25 — Plan refined: hackathon code unavailable, so this repo builds everything; macOS first for notifications (Windows supported); email mocked as an outbox folder; OpenAI-only via `shared/llm.py` with a configurable base URL for the future company gateway (Claude adapter moved to stretch).
- 2026-10-25 — Phase 3 code done (tests pass); live Webex checks pending. Decision: the v1 → v2 upgrade converts existing messages and rules instead of dropping them; focus mode starts off.
- 2026-10-26 — Built Phases 3–11 in one pass (plus README, DEMO.md, reset script): two categories + focus mode, templates + Focus Assistant space + macOS/Windows desktop alerts, shared tool registry (18 tools), OpenAI agent with slash-command fallback, summaries (on demand / focus-off / 23:59 outbox email), AI triage with focus profile + topic rules, web UI (Assistant, Triage, Rules, Summaries, Templates). 139 automated tests pass; UI smoke-tested in a browser on seeded data. Real-account checks: [VERIFY.md](VERIFY.md). One-command start: `python -m listener`.
- 2026-10-26 — Desktop alerts: osascript (built-in) is the chosen macOS mode. terminal-notifier is blocked by macOS 27 ("Notifications are not allowed"); the code falls back to osascript automatically if it's selected. Clickable alerts (VERIFY 3.10) dropped.
- 2026-10-26 — Decision: **start with no rules.** `reset_demo` deletes all rules (numbering restarts at #1); the user creates them by chatting with the assistant (or on the Rules page). With no rules, @mentions are High by default and the AI decides the rest. VERIFY.md and DEMO.md reordered: defaults + AI first, then rules by chat, then triage with those rules (including why an "always notify me when I'm mentioned" rule matters in a space marked Regular).
- 2026-10-26 — Decision (matches the hackathon setup): the assistant lives in a **space A creates by hand**, named by `ASSISTANT_SPACE_TITLE` (default "Webex Assistant"); the server only finds it, never creates it (no `spark:rooms_write` needed). Since every post is sent as A, the server's posts start with a template-driven header ("🤖 **Webex Assistant**", `templates/chat/space_post.md`) to tell them apart from A's own messages. Renamed "Focus Assistant" → "Webex Assistant" everywhere.
- 2026-10-26 — More quick commands (no AI needed): `/mode [on|off]`, `/profile [text|explain]`, `/watch [word]`, `/unwatch word`, `/topic subject`, `/rule on|off|delete N` (plus the existing `/rules`, `/summary`, `/help`). New tools: `explain_focus_profile` (the AI's own reading of what's urgent vs. what can wait, incl. what it learned from corrections), `list_watches`, `watch`, `unwatch`. `/profile` now shows the profile text, watched keywords/topics, and the correction count.
- 2026-10-26 — VERIFY.md Appendix A: every capability (22 tools + all quick commands) listed both ways, quick command and plain English. All 30 plain-English phrases pass `scripts/eval_assistant.py` with gpt-4.1-mini. New `scripts/ui_sandbox.py`: the real app on fake data (no Webex, temp DB/outbox/templates copy) with `say` to inject incoming messages, for testing the UI by hand. `TEMPLATES_DIR` is now overridable.
- 2026-10-26 — Removed all Priority bot code (`bot_send`/`bot_me`, the `bot` alert channel, `PRIORITY_BOT_TOKEN`, bot lookups in login and the pipeline). The integration stays: it's A's login for every Webex call (polling, the Webex Assistant space).
