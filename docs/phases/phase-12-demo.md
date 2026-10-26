# Phase 12 — Demo polish

**Status:** README, [DEMO.md](../DEMO.md), and `scripts/reset_demo.py` done; the two dry runs are pending ([VERIFY.md §12](../VERIFY.md#12-demo-rehearsal)).

Make the demo reliable on the company network and easy to follow.

## Action items
- [ ] `scripts/reset_demo.py`: clears messages, chat, summaries, and focus sessions; deletes all rules (the demo creates them by chat) and resets the focus profile; keeps the login and the Webex Assistant space
- [ ] `README.md`: one-time setup (integration scopes, login, assistant space, `.env`), run commands (listener + `npm run build`), company-network notes (proxy, CA bundle, and the swap points for the LLM gateway and real email), and the Claude Code MCP setup
- [ ] `docs/DEMO.md`: a step-by-step script, e.g.
  1. UI: focus **on**, show the Rules tab and the focus profile
  2. C sends 3 noisy messages → nothing pings, and Triage fills live as `regular`
  3. B sends one → desktop notification + post in the Webex Assistant space
  4. C writes "prod is down" (no rule) → AI marks it `high` and it pings
  5. In Webex chat: "notify me when Dana writes" → rule appears in the UI
  6. Triage: mark one message wrong → accuracy updates
  7. Chat: "what did I miss?" → summary
  8. `/focus off` → session summary posted; show the Summaries tab and open last night's end-of-day email (`.eml` from `data/outbox/` in Apple Mail)
  9. Templates tab: a teammate changes the alert wording → B sends again → new wording
- [ ] Refresh `docs/overview.html` (still shows v1) for sharing
- [ ] Prepare the message text for B and C ahead of time (copy and paste during the demo)
- [ ] Backup plan: slash commands if the OpenAI API fails, and a screen recording if Wi-Fi fails
- [ ] macOS demo setup: allow notifications for Script Editor (osascript alerts), turn off Focus / Do Not Disturb on the demo Mac, and mute the noisy Webex spaces
- [ ] Dry run on the demo Mac, in the same setup as the company network (polling, no bot, `NOTIFY_CHANNELS=assistant_space,desktop`)

## Checkpoint
- [ ] Two full dry runs from `reset_demo.py` to the end of the script, each under 7 minutes, with no manual fixes
