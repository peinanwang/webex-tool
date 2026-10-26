# Phase 9 — Web UI, part 2: Assistant chat & Summaries (live)

**Status: built 2026-10-26** (automated tests pass). Hands-on checks: [VERIFY.md](../VERIFY.md).

The Webex-style chat tab (the same thread as the Webex Assistant space), the summary archive, and live updates everywhere.

## Learn first
- **Server-Sent Events (SSE)**: one long-lived HTTP response that the server keeps writing small events into (`event: chat_turn`, `data: {...}`). The browser's built-in `EventSource` receives them. It's simpler than WebSockets because data only flows server → browser, and the browser sends its actions with normal POSTs.
- **In-process event bus**: when the pipeline stores a message or the agent replies, it publishes an event to an in-memory queue. Every open SSE connection reads from it. This works because the poller, agent, and API all run in one process.
- **Mirroring**: a message typed in the UI is also posted into the Webex space (as A, recorded in `app_posts` so the poller skips it). That keeps both windows identical.

## Action items

### Backend
- [ ] `listener/events.py`: `publish(type, data)` + `GET /api/events` (SSE). Events: `message_stored`, `chat_turn`, `focus_changed`, `summary_created`
- [ ] Publish from: the pipeline (after storing), the agent (each turn), focus on/off, and summary generation
- [ ] `GET /api/chat?before=` (history), `POST /api/chat {text}` → mirror the user text to Webex → `agent.handle(text, source="ui")` → reply mirrored too
- [ ] `GET /api/summaries?kind=`, `GET /api/summaries/{id}`, `POST /api/summaries {start, end, scope}`, `POST /api/summaries/{id}/email` (outbox), `GET /api/outbox/{file}` (serves the `.html` preview), `POST /api/summaries/{id}/regenerate`

### Frontend
- [ ] `useEvents()` hook (one `EventSource`, reconnects automatically). Triage, the top bar, and chat update live; the Phase 8 refresh timer goes away
- [ ] **Assistant tab**: Webex-like bubbles, "via Webex/web" tag, Markdown rendering, **cards** from `cards_json` (rule card with toggle, message card with re-mark buttons, summary card with "Email me"), quick-action chips, and a "thinking…" indicator
- [ ] **Summaries tab**: list with kind badge and ✉ status, Markdown viewer, Regenerate / Email me (writes to the outbox; shows a link to open the `.html` preview) / Copy, and a "New summary" dialog (period + scope)

## Checkpoint
- [ ] Type in the Webex space → it appears in the UI chat within about a second (plus the poll interval), and the reply appears in both
- [ ] Type in the UI → it appears in the Webex space, and the agent answers once (no duplicate turn)
- [ ] B sends a message → a new row appears at the top of Triage without a reload
- [ ] A rule card's toggle in chat → the Rules tab reflects it
- [ ] New summary from the UI → appears in the list and in the Webex space. "Email me" → a new file in `data/outbox/`, and the UI opens its preview
- [ ] Turning focus off in Webex → the top bar updates live, and the session summary appears in Summaries
