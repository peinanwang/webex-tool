# Web UI

A local web app at `http://localhost:8000`, served by the same process as the listener. Built in Phases 8, 9, and 11. Code lives in `ui/` (React + Vite + TypeScript + Tailwind). The backend routes are in `listener/api.py`.

## How chat and UI split the work

- **Chat is for intent**: "do X" or "tell me Y" in one sentence. It works from Webex on any device.
- **The UI is for review and bulk work**: looking at many messages at once, correcting the AI, seeing what a rule would change before saving it, browsing the summary archive, and editing wording.

Every UI button calls the **same tool functions** as the assistant (`shared/tools.py`), so the UI and the chat always agree. For example, toggling focus in the UI and typing `/focus off` in Webex do exactly the same thing.

## Layout

```
┌──────────┬─────────────────────────────────────────────────────────────────────┐
│  Webex   │  ● Focus ON · 1h 12m · 3 high · 27 held    [ Turn off ]   ● polling 0.5s ago │
│  Focus   ├─────────────────────────────────────────────────────────────────────┤
│          │                                                                     │
│ 💬 Assistant │                       (selected tab)                              │
│ 🗂 Triage   │                                                                     │
│ ⚙ Rules    │                                                                     │
│ 📄 Summaries│                                                                     │
│ ✏ Templates │                                                                     │
│          │                                                                     │
└──────────┴─────────────────────────────────────────────────────────────────────┘
```

The **top bar** is always visible. It shows the focus switch with a session timer and counts, plus a health dot (time of the last successful poll, whether the OpenAI API is reachable). Updates arrive live through Server-Sent Events (`/api/events`).

## 💬 Assistant (Phase 9)

The same thread as the Webex Assistant space, styled like Webex, with richer rendering.

```
┌───────────────────────────────────────────────────────────────┐
│  Webex Assistant                                   via Webex ⓦ │
│                                                               │
│  You  10:02  notify me when Bob writes                        │
│  🤖   10:02  ✅ Added rule #5: messages from bob@acme.com → High │
│              ┌───────────────────────────────┐                │
│              │ #5  sender = bob@acme.com  High  [on ●] [delete]│  ← rule card
│              └───────────────────────────────┘                │
│  You  11:30  what did C say today?                    via web │
│  🤖   11:30  C sent 4 messages, mostly about lunch plans…      │
│              ┌ 09:14 Team Chat  "anyone for lunch?"  Regular [↑ High] ┐ ← message cards
│              └ 10:40 A↔C        "deck is ready"      Regular [↑ High] ┘
│                                                               │
│  [Summarize today] [Focus off] [Show rules] [What did I miss?] │  ← quick actions
│  ┌──────────────────────────────────────────────────┐ [Send]  │
│  │ Ask anything…                                     │         │
└───────────────────────────────────────────────────────────────┘
```

- Tool results that came with structured `data` render as **cards** with buttons (toggle a rule, re-mark a message, email a summary). In Webex, the same reply is the plain template text.
- **Quick-action chips** send common prompts or slash commands.
- A "via Webex" or "via web" tag on each turn shows where it was typed. Messages sent from the UI are mirrored into the Webex space, so the thread is identical in both places.

## 🗂 Triage (Phase 8)

Review what was sorted where, and correct it. Each correction makes triage measurably better, because corrections become examples for AI triage in Phase 10.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Today ▾   [All 42] [High 5] [Regular 37] [Needs review 9]   🔍 search    │
│ Reviewed 12 · Accuracy 92% (rules 100%, AI 85%)                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 14:05  Bob · A↔B         "Can you approve the PR by 3?"   HIGH           │
│        why: rule #2 sender=bob@acme.com                  [✓] [↓ Regular] │
│ 13:50  Carol · Team Chat "prod latency spiking again"     HIGH   AI      │
│        why: AI: reports a production issue               [✓] [↓ Regular] │
│ 13:20  Carol · Random    "cake in the kitchen 🎂"         REGULAR        │
│        why: default                                       [✓] [↑ High]   │
└─────────────────────────────────────────────────────────────────────────┘
  Click a row → side panel: full text · space · whether A was mentioned · focus on/off at the time
                · [Create rule from this ▾  sender / space / keyword]  · [Test current rules on it]
```

- **Filters**: by day or period, category, sender, space, and "Needs review" (AI-decided messages not reviewed yet).
- **Feedback buttons** call `mark_message`. The row shows the correction, and the accuracy figure updates.
- **"Create rule from this"** opens the Rules form pre-filled. This is the fastest way to turn a correction into a rule.

## ⚙ Rules (Phase 8)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Rules (high beats regular · ties → oldest)                [+ New rule] │
├──────────────────────────────────────────────────────────────────────┤
│ #1  When I'm @mentioned                       → High      [on ●]  🗑   │
│ #2  Messages from bob@acme.com                → High      [on ●]  🗑   │
│ #3  Messages containing "urgent"              → High      [off ○] 🗑   │
│ #4  Anything in "Random"                      → Regular   [on ●]  🗑   │
├──────────────────────────────────────────────────────────────────────┤
│ New rule:  [High ▾]  when  [sender ▾]  is  [bob@… (autocomplete) ]    │
│            Preview: would change 3 of today's 42 messages  [show]      │
│                                                     [Cancel] [Save]   │
├──────────────────────────────────────────────────────────────────────┤
│ Try it: sender [carol@…] space [Team Chat] text [server down] [☐ @me]  │
│         → HIGH because rule #3 keyword=urgent … (or "default")         │
├──────────────────────────────────────────────────────────────────────┤
│ Focus profile (AI triage, Phase 10):                                  │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ I'm on the payments team. Outages, anything from my manager, and │ │
│ │ direct questions with a deadline are urgent. Social chat isn't.   │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

- Rules are written in plain English (the same text as the `rules_list` template).
- Autocomplete for senders and spaces comes from people and spaces already in the DB, so A doesn't have to type emails.
- The **impact preview** re-runs the rules over today's stored messages with and without the new rule (`POST /api/rules/preview`), so A sees the effect before saving.

## 📄 Summaries (Phase 9)

```
┌───────────────────────────┬────────────────────────────────────────────┐
│ [+ New summary]           │  # Thursday, Oct 23 — what you missed      │
│                           │  42 messages · 5 high · 37 regular         │
│ Oct 23  End of day  ✉ out │                                            │
│ Oct 23  Focus 13:00–15:10 │  ## Highlights                             │
│ Oct 23  On demand  (all)  │  - Release moved to Friday (Carol, Team…)  │
│ Oct 22  End of day  ✉ out │  ## Action items for you                   │
│ …                         │  - [ ] Approve Bob's PR by 3pm             │
│                           │                                            │
│ Filter: [All kinds ▾]     │      [Regenerate] [Email me] [Copy]        │
└───────────────────────────┴────────────────────────────────────────────┘
  New summary: period [Today ▾ / custom range]  scope [What I missed | Everything]
```

## ✏ Templates (Phase 11)

For non-technical teammates. They change the wording, not the code.

```
┌──────────────────────────┬───────────────────────────────┬──────────────────────────┐
│ Notifications            │ notify/assistant_post.md      │ Preview (sample data)    │
│  › Assistant space post  │ ┌───────────────────────────┐ │ 🔔 **Bob** in A↔B        │
│  › Desktop title / body  │ │🔔 **{{ sender }}** in      │ │ Can you approve the PR   │
│ Chat replies             │ │{{ space }}                │ │ by 3?                    │
│  › Help · Rule added · … │ │{{ text }}                 │ │ _why: rule #2 sender=…_  │
│ Summaries                │ │_why: {{ reason }}_        │ │                          │
│  › Summary layout · Email│ └───────────────────────────┘ │                          │
│ AI prompts               │ Available: sender, space,     │                          │
│  › Assistant persona     │ text, reason, time, link      │                          │
│  › Triage · Summarize    │      [Reset to default] [Save]│                          │
└──────────────────────────┴───────────────────────────────┴──────────────────────────┘
```

- **Save** first renders the template with the sample data. If a placeholder is misspelled or the syntax is broken, it shows a plain-language error and does not save.
- **Reset to default** restores the version that ships with the repo.

## API the UI uses (`listener/api.py`)

| Endpoint | Calls |
|---|---|
| `GET /api/status` · `POST /api/focus` | `get_focus_status` · `set_focus_mode` |
| `GET /api/messages?…` · `POST /api/messages/{id}/feedback` · `GET /api/triage/stats` | `search_messages` · `mark_message` · `get_triage_stats` |
| `GET/POST /api/rules` · `PATCH/DELETE /api/rules/{id}` · `POST /api/rules/test` · `POST /api/rules/preview` | rule tools + preview helper |
| `GET /api/contacts?q=` · `GET /api/spaces?q=` | `find_contacts` · `find_spaces` |
| `GET /api/chat` · `POST /api/chat` | chat history · `agent.handle(text, source="ui")` |
| `GET/POST /api/summaries` · `POST /api/summaries/{id}/email` · `GET /api/outbox/{file}` | summary tools · email outbox preview |
| `GET/PUT /api/templates/{name}` · `POST /api/templates/{name}/preview` | template store |
| `GET /api/events` | Server-Sent Events: `message_stored`, `chat_turn`, `focus_changed`, `summary_created` |

## Testing the UI

Three levels, from fastest to most realistic:

| Level | How | What it proves |
|---|---|---|
| **API tests** (automated) | `pytest tests/test_api.py` | Every endpoint the UI calls returns the right data and friendly errors. No browser, no Webex |
| **UI sandbox** (by hand) | `./dev.sh sandbox` → http://localhost:5173 (dev server with instant reload), or `python -m scripts.ui_sandbox` → http://localhost:8765 (built UI); then `python -m scripts.ui_sandbox say <bob\|carol\|dana> "<text>" [--space Team] [--mention]` to make messages arrive | The real page, API, triage (incl. AI if a key is set), live updates, chat, summaries, and the Templates editor, on fake data. Webex is disconnected; the DB, outbox, and a copy of `templates/` live in a temp folder |
| **Real accounts** (by hand) | `python -m listener` + accounts A/B/C, following [VERIFY.md §10](VERIFY.md#10-the-web-page-tab-by-tab) | Everything, including the Webex ↔ page mirroring |

Next step, if wanted: **automated browser tests** with Playwright (`ui/tests/*.spec.ts`), run against the sandbox. They'd click through the main flows (toggle focus, receive a message, correct it, add a rule with preview, edit a template) on every change.
