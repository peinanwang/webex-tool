# Phase 7 — Demo polish

Make the demo reliable and easy to follow.

## Action items
- [ ] In the Webex client as A: mute the A↔C and group spaces; leave only the Priority bot 1:1 unmuted
- [ ] `scripts/reset_demo.py`: clears `messages`, re-seeds rules, removes today's digest
- [ ] `README.md`: one-time setup and run commands for both modes (webhook: ngrok + listener; polling: listener only), plus Claude Code
- [ ] `docs/DEMO.md`: a step-by-step script, e.g.
  1. Show the rules (MCP: "show my rules")
  2. C sends 3 noisy messages → nothing pings
  3. B sends one → Priority bot pings instantly
  4. C @mentions A → it gets through
  5. Add a rule live ("notify me about 'outage'") → C says "outage" → it pings
  6. "Summarize what I missed" → held-only digest file appears
  7. (Optional) "Summarize everything today" → full conversation summary including relayed messages and A's replies
- [ ] Decide the demo mode for the venue: webhook if ngrok works there, otherwise polling (mention the ~10s delay when presenting)
- [ ] Do one dry run on the actual company network in polling mode
- [ ] Backup plan: switch `LISTENER_MODE` and restart if one mode fails; keep a recorded screen capture in case Wi-Fi fails
- [ ] Prepare the message text for B and C ahead of time (copy and paste during the demo)

## Checkpoint
- [ ] Two full dry runs from `reset_demo.py` to digest, each under 5 minutes, with no manual fixes
