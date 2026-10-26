# Verification guide (Phases 3–6)

Hands-on checks that prove each piece works with real Webex messages. Each section says **what it proves**, **what to do**, and **what you should see**. Tick the matching checkpoint boxes in `docs/phases/` as you go.

Accounts: **A** = you (filtered user), **B** = important sender, **C** = noisy sender.

## 0. Setup (once per test session)

```bash
cd /Users/peinanwang/playground/webex-tool
source .venv/bin/activate
```

**Optional fresh start.** This clears stored messages and polling state but keeps your login and rules:
```bash
sqlite3 data/focus.db "DELETE FROM messages; DELETE FROM kv WHERE key LIKE 'poll_%';"
```

**Handy query** (used throughout; shows the newest 10 messages):
```bash
sqlite3 -header -column data/focus.db \
  "SELECT substr(created,12,8) AS utc, person_email, room_title, status, reason, mentioned_me,
          relayed_at IS NOT NULL AS pinged, substr(text,1,30) AS text
   FROM messages ORDER BY created DESC LIMIT 10"
```

---

## 1. Rules engine unit tests (Phase 4)

**Proves:** the decision logic is right: precedence (ignore > notify > digest), defaults, case-insensitive matching, disabled rules, and "rules beat defaults".

```bash
pytest -v
```
**Expect:** `12 passed`. No Webex, ngrok, or listener needed.

---

## 2. Seed the demo rules (Phase 4)

**Proves:** rules can be created and listed; sets up the rules the next sections rely on.

```bash
python -m scripts.seed_rules --reset --important <B's email>
```
**Expect:**
```
Rules now:
  notify  rule#1 mention
  notify  rule#2 keyword=urgent
  notify  rule#3 sender=<B's email>
```
`--reset` deletes existing rules first. Add `--ignore-space "<space title>"` to also try an ignore rule.

---

## 3. Webhook mode, end to end (Phases 3 + 4)

**Proves:** Webex delivers each new message to the listener through ngrok within about a second; the listener fetches it, applies the rules, stores it with a status and reason, and the Priority bot pings you for `notify` messages.

**Terminal 1:** `ngrok http 8000`
**Terminal 2:** `uvicorn listener.main:app --port 8000` (with `LISTENER_MODE=webhook` in `.env`)

**Expect at startup:** `Mode: webhook. Registered → https://…/webhook`

Then send these and watch Terminal 2, your Webex, and the handy query:

| # | Send | Terminal 2 shows | Bot pings A? | Proves |
|---|---|---|---|---|
| 3a | **B → A** in their 1:1: "can you review this?" | `[notify] … (rule#3 sender=…)` | ✅ | Sender rule + relay |
| 3b | **C → A** in their 1:1: "lunch?" | `[digest] … (default)` | ❌ | Unmatched → held silently |
| 3c | **C** in the group: "anyone seen the new office?" | `[digest] … (default)` | ❌ | Group messages are captured too |
| 3d | **C** in the group: "@A quick question" | `[notify] … (rule#1 mention)`, `mentioned_me=1` | ✅ | Mention detection + mention rule |
| 3e | **C → A**: "urgent: build is broken" | `[notify] … (rule#2 keyword=urgent)` | ✅ | Keyword rule (case-insensitive) |
| 3f | **A** replies anywhere | `[self] … (self)` | ❌ | Your messages are kept for context, never relayed |
| 3g | (automatic) the bot's own pings | nothing logged | n/a | No notification loop |

**The ping** appears in your 1:1 with the Priority bot, like:
```
🔔 Important Pat W in a direct message:
can you review this?
why: rule#3 sender=…
```

**Security check (optional)**, from a third terminal while the listener runs:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/webhook -d '{}'
```
**Expect:** `401`. Requests without a valid Webex signature are rejected.

**Webhook inspector (optional):** http://127.0.0.1:4040 shows every request Webex sent.

---

## 4. Polling mode (Phase 3)

**Proves:** the listener works with **no ngrok and no public URL** (the company-network setup), doesn't import old history, catches up after downtime, and never stores a message twice.

1. Stop the listener (Ctrl+C) and ngrok. In `.env` set `LISTENER_MODE=polling`.
2. Start: `uvicorn listener.main:app --port 8000`
   **Expect:** `Mode: polling every 10s (no ngrok needed)`. `curl localhost:8000/health` shows `"mode": "polling"`.

| # | Do | Expect | Proves |
|---|---|---|---|
| 4a | Just start it (first time in polling mode) | No old messages appear | No history import (`poll_started_at` = now) |
| 4b | **B → A**: "polling test" | Within ~10s: `[notify] …` and a ping | Polling picks up new messages; rules and relay work the same |
| 4c | Stop the listener. **C → A**: "sent while you were down". Start it again | Within ~10s of startup: `[digest] … sent while you were down` | Catch-up after downtime (saved cursors) |
| 4d | Restart once more without sending anything | Nothing new logged; the handy query shows no duplicate rows | No duplicates |

3. When done, set `LISTENER_MODE=webhook` again if you want webhook mode back. Webhook mode re-registers its webhook on startup.

**Contrast with webhook mode (optional):** in webhook mode, stop the listener, send a message, start again. That message is **not** picked up, because Webex doesn't replay missed webhooks. That's the trade-off between the two modes.

---

## 5. MCP server in Claude Code (Phase 5)

**Proves:** you can manage rules and query messages in plain English from Claude Code, and rule changes apply to the very next message without restarting the listener.

**One-time manual step:** `.mcp.json` registers the server for this project. Claude Code only loads it in a **new session**, and asks you to **approve** it the first time:
1. Start a new Claude Code session in this folder (in VS Code, open a new Claude Code conversation; in a terminal, run `claude` here).
2. Approve the `webex-focus` server when prompted.
3. Run `/mcp`. **Expect:** `webex-focus` connected with 10 tools.

(VS Code Copilot instead: `.vscode/mcp.json` is already there; start it from Copilot Chat's tools/MCP list.)

Keep the listener running (either mode), then ask Claude:

| # | Ask Claude | Expect | Proves |
|---|---|---|---|
| 5a | "Show my Webex Focus rules" | The 3 seeded rules | `list_rules` |
| 5b | "Notify me about anything that says 'outage'" | A new `notify keyword=outage` rule | `add_rule` |
| 5c | **C → A**: "outage in region 2" | `[notify] … keyword=outage` + ping | Rules apply live, no restart |
| 5d | "If C writes 'lunch?' in the group, would I get pinged?" | "No: digest (default)" | `test_rule` dry run |
| 5e | "Pause the urgent rule", then **C**: "urgent?" | Rule disabled; message is `digest`, no ping | `set_rule_enabled` |
| 5f | "Turn the urgent rule back on" and "delete the outage rule" | Confirmations; `list_rules` reflects both | Re-enable + `delete_rule` |
| 5g | "What did C send me today?" | C's messages with times and statuses | `get_messages` (sender filter) |
| 5h | "Why didn't I get pinged for C's lunch message?" | Explains `digest` / `default`: no rule matched | The `reason` field |
| 5i | "Add a rule to notify me loudly about bob" | Claude explains that "loudly" isn't a valid action (or picks `notify`) | Input validation reaches the model |

---

## 6. Digest (Phase 6)

**Proves:** summaries work for any period, in both scopes, are saved to files, and are honest about missing data.

Send a few more mixed messages from C first (5–10 on different topics) so there's something to summarize.

| # | Ask Claude | Expect | Proves |
|---|---|---|---|
| 6a | "Summarize what I missed today" | Only held (`digest`) messages, grouped by space, with action items; saved as `data/digests/<today>_held.md` | `scope=held`, default period, `save_digest` |
| 6b | "Summarize everything today" | Includes B's relayed messages and your own replies; saved as `<today>_all.md` | `scope=all`, both sides of conversations |
| 6c | "Summarize everything from yesterday to today" | A range summary; file `<yesterday>_<today>_all.md` | Custom periods |
| 6d | "Summarize what I missed on 2026-01-01" | Says there's no data for that period (the listener wasn't running) | Gap reporting (`data_starts_at`) |
| 6e | Repeat 6a | Same file name, overwritten (no duplicates) | Clean re-runs |
| 6f | "List my digests" / "show today's held digest" | File names; then the content | `list_digests`, `read_digest` |
| 6g | Use the prompt: type `/` in Claude Code and pick the webex-focus `daily_digest` prompt | Same as 6a in one step | The `daily_digest` prompt |

Check the files directly: `ls data/digests/ && cat data/digests/<today>_held.md`

---

## 7. Reset and cleanup commands

| Goal | Command |
|---|---|
| Clear messages + polling state (keep login and rules) | `sqlite3 data/focus.db "DELETE FROM messages; DELETE FROM kv WHERE key LIKE 'poll_%';"` |
| Reset rules to the demo set | `python -m scripts.seed_rules --reset --important <B's email>` |
| Delete digests | `rm data/digests/*.md` |
| Start completely fresh (requires login again) | `rm data/focus.db* && python -m shared.db && python -m scripts.login` |

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| No line in Terminal 2 when B sends (webhook mode) | Check http://127.0.0.1:4040: no request means the webhook isn't registered or ngrok restarted. Restart the listener (it re-registers). |
| `[error] relay failed …` | The message is stored, but the bot couldn't send. Check `PRIORITY_BOT_TOKEN` in `.env`. |
| `Not logged in. Run: python -m scripts.login` | Run it with the listener **stopped** (both use port 8000). |
| `Address already in use` | Something else is on port 8000: `lsof -nP -iTCP:8000 -sTCP:LISTEN` |
| Polling picks up nothing | Wait one full `POLL_INTERVAL`. Messages sent before polling mode was first started are skipped by design. |
| `/mcp` doesn't list webex-focus | Start a **new** Claude Code session in this folder and approve the server. |
| Claude says a tool failed | Run `python mcp_server/server.py` directly; an import error will show (Ctrl+C to exit). |
| Times look off by hours | Stored times are UTC; MCP tools show local time. The handy query shows UTC. |
