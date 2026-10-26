# Webex Focus — Roadmap

Goal: keep Webex quiet except for messages that match A's rules. Matching messages get relayed by the Priority bot. Everything else is logged and summarized later through an MCP server.

**Two listener modes:** `webhook` (instant, uses ngrok; for home/personal setup) and `polling` (checks every 10–15s, outbound only; for the company network where ngrok is likely blocked). Both feed the same pipeline, so rules, bot relay, MCP, and digest work the same either way.

Work one phase at a time. A phase is done only when its **checkpoint** passes. Detailed action items for each phase are in [`phases/`](phases/). Hands-on checks for Phases 3–6 are in [VERIFY.md](VERIFY.md).

## Phases

- [x] **Phase 0 — Accounts & Webex setup** → [details](phases/phase-0-setup.md)
  Checkpoint: 3 accounts, 3 test spaces, Priority bot and integration created, ngrok installed.
- [x] **Phase 1 — Project scaffold & database** → [details](phases/phase-1-scaffold.md)
  Checkpoint: `python -m shared.db` creates `data/focus.db` with all tables.
- [x] **Phase 2 — OAuth login & Webex client** → [details](phases/phase-2-oauth.md)
  Checkpoint: `python -m scripts.login` stores a refresh token, and `webex_client.me()` returns A's profile, refreshing the token if needed.
- [ ] **Phase 3 — Listener: receive & log messages (webhook + polling modes)** → [details](phases/phase-3-listener.md)
  Checkpoint: in **both** `LISTENER_MODE=webhook` and `LISTENER_MODE=polling`, B or C sends a message, and a row shows up in `messages` with full text (status `digest`, reason `default`).
- [ ] **Phase 4 — Rules engine & Priority bot relay** → [details](phases/phase-4-rules.md)
  Checkpoint: B's message gets relayed by the Priority bot, C's is logged silently, and an @mention of A gets relayed.
- [ ] **Phase 5 — MCP server: rules & message queries** → [details](phases/phase-5-mcp.md)
  Checkpoint: from Claude Code, "add a notify rule for keyword 'outage'" works, and "what did C say today?" answers from the DB.
- [ ] **Phase 6 — Digest** → [details](phases/phase-6-digest.md)
  Checkpoint: "summarize what I missed today" (held only) and "summarize everything from Monday to Wednesday" (all messages, custom period) both produce saved digest files.
- [ ] **Phase 7 — Demo polish** → [details](phases/phase-7-demo.md)
  Checkpoint: the full demo script runs end to end in under 5 minutes, twice in a row.

## Stretch goals (only after Phase 7)

- [ ] Scheduled daily digest reminder (APScheduler)
- [ ] Optional LLM triage for unmatched messages (needs an API key in the listener)
- [ ] Web UI in `ui/` for rules and message log
- [ ] Use Webex's hosted Messaging/Meetings MCP alongside ours (e.g. reply from Claude Code); see [webex-mcp-analysis.md](webex-mcp-analysis.md)

## Status log

Add a dated line each time a phase is finished or a decision changes.

- 2026-10-21 — Project started. Accounts A, B, C registered.
- 2026-10-21 — Polling moved from stretch goal into Phase 3 as a second listener mode, so the demo can run on the company network without ngrok.
- 2026-10-21 — Summaries support custom periods and two scopes (`held` / `all`). A's own messages are now stored as `status='self'` (never relayed) so "all" summaries show both sides of conversations.
- 2026-10-21 — Decided to build our own MCP server instead of using Webex's hosted MCP; see [webex-mcp-analysis.md](webex-mcp-analysis.md).
- 2026-10-21 — Phase 0 done: accounts, spaces, Priority bot, integration, ngrok. Company network questions for IT still open.
- 2026-10-21 — Phase 1 done: scaffold, config, SQLite (WAL) with kv/messages/rules.
- 2026-10-21 — Phase 2 done: OAuth login (with `--paste` fallback), auto token refresh, Webex client helpers, bot test message delivered.
- 2026-10-22 — Built Phase 3 polling mode and Phases 4–6 (rules engine + relay, MCP server, digest). Unit tests and tool checks pass; checkpoints with real messages are in [VERIFY.md](VERIFY.md). Decision: rules always beat defaults; `notify mention` is seeded as an explicit rule.
