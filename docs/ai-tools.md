# What the AI assistant can do

A talks to the assistant in plain language, in the Webex **Focus Assistant** space or the UI's **Assistant** tab (same conversation). The assistant is an LLM (OpenAI API; later the company's OpenAI-compatible gateway) with the **tools** below. A tool is a Python function the model can ask us to run. The model picks the tool and fills in its arguments, we run it, and the model writes the answer from the result.

The same tools are exposed to Claude Code / Copilot through the MCP server. That gives us a free test bench before the in-app agent exists (Phase 5), and power users get the same features from their IDE.

Code: `shared/tools.py` (registry), `shared/agent.py` (chat loop), `mcp_server/server.py` (MCP adapter).

## Tool catalog

✏️ = changes data. ⚠️ = the assistant confirms with A before calling it.

### Focus mode

| Tool | What it does | A might say |
|---|---|---|
| `get_focus_status()` | On/off, since when, and how many high/regular messages so far this session | "Am I in focus mode?" · "How much have I missed?" |
| `set_focus_mode(on)` ✏️ | Turns focus on or off. Turning it **off** ends the session and generates a "what you missed" summary (Phase 7) | "Focus on" · "I'm done focusing" |

### Rules

| Tool | What it does | A might say |
|---|---|---|
| `list_rules()` | All rules in plain English, with id and on/off state | "What are my rules?" |
| `add_rule(category, match_type, value)` ✏️ | `category`: `high` or `regular`. `match_type`: `sender`, `space`, `keyword`, `mention`, or `topic` (Phase 10: a description in plain language, judged by AI) | "Notify me when Bob writes" · "Anything in Random is regular" |
| `set_rule_enabled(rule_id, enabled)` ✏️ | Pause or resume a rule without deleting it | "Pause the 'urgent' rule" |
| `delete_rule(rule_id)` ✏️⚠️ | Remove a rule | "Delete the rule about Random" |
| `test_rule(text, sender, space, mentioned)` | Dry run: which category would a message like this get, and why? Nothing is stored | "If C says 'server down' in Team Chat, would I get pinged?" |
| `find_contacts(query)` | Name → email, from people who have messaged A (with a Webex People API fallback) | used automatically by "notify me when **Bob** writes" |
| `find_spaces(query)` | Partial name → space title, from spaces we've seen | used automatically by "mute **the design channel**" |

### Messages & triage

| Tool | What it does | A might say |
|---|---|---|
| `search_messages(category, sender, space, contains, start, end, limit)` | Look up stored messages, newest first, each with its category and reason | "What did C say today?" · "Anything about the release this week?" |
| `get_triage_stats(start, end)` | Counts per category, how many A has reviewed, and accuracy based on A's corrections | "How accurate was triage today?" |
| `mark_message(message_id, label)` ✏️ | Feedback: `correct`, `should_be_high`, `should_be_regular`. Feeds the Triage tab and AI triage examples | "That message from C was actually important" |

### Summaries

| Tool | What it does | A might say |
|---|---|---|
| `summarize(start, end, scope)` ✏️ | Builds a summary for any period. `scope`: `held` (regular only, "what I missed") or `all` (everything, both sides of each conversation). Saved to the DB | "Summarize what I missed" · "Summarize Monday to Wednesday" |
| `list_summaries(kind, limit)` | Past summaries. `kind`: `on_demand`, `focus_session`, `end_of_day` | "Show me last week's summaries" |
| `get_summary(summary_id)` | One saved summary | "Show Tuesday's end-of-day summary" |
| `email_summary(summary_id)` ✏️ | "Email" a saved summary to A. For now this writes an `.eml` + `.html` to `data/outbox/` (mock); real delivery comes later | "Email me that" |

### AI triage settings (Phase 10)

| Tool | What it does | A might say |
|---|---|---|
| `get_focus_profile()` | A's description of what matters, used by AI triage | "What do you think is important to me?" |
| `set_focus_profile(text)` ✏️ | Replace that description | "Outages and anything from my manager are urgent; social chat isn't" |

## Slash commands (no LLM needed)

These run instantly and deterministically, even if the LLM is down or out of quota. That makes them handy for the demo and for people who prefer commands.

| Command | Same as |
|---|---|
| `/help` | Lists what the assistant can do (`templates/chat/help.md`) |
| `/status` | `get_focus_status()` |
| `/focus on` · `/focus off` | `set_focus_mode(...)` |
| `/rules` | `list_rules()` |
| `/summary` · `/summary focus` | `summarize(today, held)` · summary of the current or last focus session |

## How a chat turn works

```
A types in the Focus Assistant space ──► poller sees A's message in that space
                                          │ (not one we posted ourselves: app_posts check)
                                          ▼
                               starts with "/"? ── yes ──► run tool ─► render template ─┐
                                          │ no                                          │
                                          ▼                                             │
             LLM(system prompt + last 20 turns + tool list)                             │
                 ├─ asks for a tool ─► run it ─► result (data + rendered text) ─► LLM   │
                 │        (repeat, up to AGENT_MAX_STEPS = 5)                           │
                 └─ final answer ─► templates/chat/answer.md ───────────────────────────┤
                                                                                        ▼
                         post reply into the space as A (integration), record its id in app_posts,
                         save both turns in chat_messages, push to the UI (Phase 9)
```

## How responses stay template-driven

Every response is written from a template in `templates/` (see [Phase 4](phases/phase-4-templates-relay.md) and [Phase 11](phases/phase-11-template-editor.md)):

1. **Tool results.** Each tool returns `{"data": ..., "display": "<rendered template>"}`. The system prompt tells the model to reply with `display` as-is when it answers the request (for example, the rules list or "rule added"). So rule lists, confirmations, and errors look the same every time.
2. **Free-form answers** ("what did C say?") are written by the model, guided by the tone and persona in `templates/prompts/assistant.md`, and wrapped by `templates/chat/answer.md` (for example, to add a footer).
3. **Summaries.** The model returns structured JSON (headline, highlights, per-space points, action items). `templates/summary/summary.md` controls the layout. The email uses `summary/email_subject.txt`, `summary/email_body.html`, and `summary/email_body.txt`.
4. **Notifications.** `templates/notify/assistant_post.md` (the post in the Focus Assistant space) and `notify/desktop_title.txt` / `desktop_body.txt` (the desktop notification).

## What the assistant will not do (v2)

- Send or reply to messages in other spaces on A's behalf (stretch goal: drafts only)
- Read Webex history from before the listener first started
- Mute or unmute Webex spaces, or set Do Not Disturb (no Webex API for this; A does it in the Webex client)
- Delete messages, or change anything in Webex besides posting in the Focus Assistant space
