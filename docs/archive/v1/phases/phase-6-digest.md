# Phase 6 — Digest

Summarize messages for any period. The summary is written by the host model (Claude/Copilot), so the listener needs no LLM key.

Two scopes:

| Scope | Includes | Answers |
|---|---|---|
| `held` (default) | `digest` (and `ignore` if `include_ignored=True`) | "What did I miss?" |
| `all` | `notify`, `digest`, `ignore`, `self` | "What happened?" (with both sides of each conversation) |

All spaces are covered: 1:1s, group spaces, and team channels.

## Action items
- [x] MCP tool `get_digest_input(start=None, end=None, scope="held", include_ignored=False)`:
  - [x] Default period: today (local time, 00:00 to now); a single date is just `start=end=date`
  - [x] Accept ISO dates/times; the host model turns "Monday to Wednesday" into dates
  - [x] Returns messages grouped by space, oldest first, with sender, time, text, status, and reason
  - [x] Includes counts (relayed vs. held vs. ignored) and the time of the oldest stored message, so the model can say "no data before X"
  - [x] Caps output size (e.g. 500 messages) and says when it truncated
- [x] MCP tool `save_digest(markdown, start, end, scope)`: writes `data/digests/<start>[_<end>]_<scope>.md` (e.g. `2026-10-21_held.md`, `2026-10-19_2026-10-21_all.md`)
- [x] MCP tool `list_digests()` / `read_digest(filename)`
- [x] MCP prompt (`@mcp.prompt`) `daily_digest(start, end, scope)`: tells the model to call `get_digest_input`, summarize by space with action items and anything addressed to A, mention gaps (no data before the listener started), then call `save_digest`

## Checkpoint
- [ ] Send 5–10 messages from C (mixed topics), plus a couple from B and A
- [ ] "Summarize what I missed today" → only held messages; file `<today>_held.md` saved
- [ ] "Summarize everything today" → includes B's relayed messages and A's own replies; file `<today>_all.md` saved
- [ ] "Summarize everything from <yesterday> to today" → custom range works
- [ ] Asking for a period before the listener started → the summary says there's no data for that period
- [ ] Re-running the same request overwrites its file cleanly
