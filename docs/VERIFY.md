# Verify plan — Webex Focus (user experience)

A hands-on checklist written from the user's side: **who sends what, and what you should see.** No code reading needed. Tick the boxes as you go.

**Who's who**

|       | Account               | Role                                                                              |
| ----- | --------------------- | --------------------------------------------------------------------------------- |
| **A** | You                   | The person who wants to focus. Owns the integration. Runs Webex Focus on the Mac. |
| **B** | "Important" colleague | A will tell the assistant that B's messages should always come through.           |
| **C** | "Noisy" colleague     | Most of their messages can wait.                                                  |

**Spaces you'll use**

| Space               | Members | Used for                                                                   |
| ------------------- | ------- | -------------------------------------------------------------------------- |
| **A↔B**             | A, B    | 1:1 chat                                                                   |
| **A↔C**             | A, C    | 1:1 chat                                                                   |
| **Team** (group)    | A, B, C | Group space, @mentions                                                     |
| **Webex Assistant** | A only  | You create it (0.2). A chats with the assistant here, and alerts land here |

**How the Webex Assistant space works**

Everything in it is sent through your own login, so Webex shows **you** as the sender of every message there. The assistant's messages start with a header line: **🤖 Webex Assistant** for replies, **🔔 Webex Assistant** for alerts and summaries. Your own messages have no header.

**How a message is sorted**

1. **Your rules** decide first. You create them by chatting with the assistant (or on the Rules page). When several match, **High wins**.
2. **No rule matched?** An @mention of you is **High**.
3. Otherwise the **AI** decides High or Regular from your focus profile (or it's **Regular** if the AI is off).

You start with **no rules**, so at first only steps 2 and 3 apply.

**Timing:** new messages are picked up every ~2 seconds. Expect things to show up **2–5 seconds** after they're sent (a few seconds more when the AI is deciding).

**Every capability at a glance**, both as a quick command and in plain English, is in [Appendix A](#appendix-a--every-capability-both-ways).

**AI answers vary.** Where this plan quotes the assistant, the wording is "something like". The meaning should match. Where the AI decides a category, an occasional different call is fine: correct it in Triage (section 7).

**"Alert"** below means **both** a desktop notification **and** a 🔔 post in the Webex Assistant space.

Tip: keep three windows side by side: Webex as **A**, the Webex Focus web page (`http://localhost:8000`), and Webex as **B** or **C** (another browser profile at web.webex.com, or a phone).

---

## 0. One-time setup

### 0.1 Install and configure

- [x] In the project folder: `source .venv/bin/activate && pip install -r requirements.txt`
- [x] Build the web page: `cd ui && npm install && npm run build && cd ..`
- [x] Desktop alerts use macOS's built-in notifications: `DESKTOP_NOTIFIER=osascript` in `.env`
- [x] Open `.env` (copy any new lines from `.env.example`) and set at least:
  - `OPENAI_API_KEY=` your key
  - `LLM_MODEL=` a model your key can use (list them: `python -m shared.llm --models`)
  - `LISTENER_MODE=polling`
  - `NOTIFY_CHANNELS=assistant_space,desktop`
- [x] Check the AI connection: `python -m shared.llm "say hi"` → a short greeting

### 0.2 Log in and create your Webex Assistant space

- [x] developer.webex.com → My Webex Apps → your integration → tick **spark:all** → **Save**
- [x] In `.env`: `WEBEX_SCOPES=spark:all spark:kms` (the login must ask for exactly what's ticked)
- [x] Log in again as A: `python -m scripts.login` (Accept in the browser). The first line printed shows which scopes it asks for
  - "invalid_scope"? Something it asks for isn't ticked on the integration. The error message lists what it asked for
- [x] `python -m shared.webex_client` → shows A's name
- [x] In Webex (as A): **+** → **Create a space** → name it exactly **Webex Assistant** → don't add anyone → Create. (Already have the old "Focus Assistant" space? Rename it to Webex Assistant instead, or delete it.)
- [x] `.env` has `ASSISTANT_SPACE_TITLE=Webex Assistant` (the exact space name) and `ASSISTANT_NAME=Webex Assistant` (the name shown on the assistant's messages)
- [x] `python -m scripts.setup_assistant_space --hello` → "Found the 'Webex Assistant' space", and the help text appears in that space, starting with **🤖 Webex Assistant**

### 0.3 Mac settings

- [x] Test a desktop alert: `python -m shared.desktop_notify "Test" "Hello"` → a notification appears top-right
  - Nothing appears? System Settings → Notifications → **Script Editor** → Allow notifications, and make sure Focus / Do Not Disturb is off.
- [x] In the Webex app, signed in as A: **mute** A↔B, A↔C, and Team (right-click the space → Notifications → Mute). Webex can't be silenced by an app, so you mute it and Webex Focus decides what reaches you.

### 0.4 Start clean

- [x] Stop Webex Focus if it's running (Ctrl+C)
- [x] `python -m scripts.reset_demo` (no arguments) → "Reset done. Focus is OFF. Rules: none."
- [x] Start Webex Focus: `python -m listener`

**You should see** in the terminal:

- [ ] `Assistant space found: 'Webex Assistant' (chat with the assistant there)`
- [ ] `Mode: polling every 2.0s`
- [ ] `Focus mode: OFF · AI: <your model> · AI triage: on · alerts: assistant_space,desktop`
- [ ] `UI: http://localhost:8000`

---

## 1. First look

| #   | Do                                         | You should see                                                                                                                                                     |
| --- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1.1 | In the**Webex Assistant** space, type `hi` | Your`hi` shows as a normal message from you. A few seconds later, another message from you starting with **🤖 Webex Assistant**: that's the assistant's reply      |
| 1.2 | Open`http://localhost:8000`                | The web page. Sidebar: Assistant, Triage, Rules, Summaries, Templates. Top bar:**Focus OFF**, a green "Listening · Ns ago" dot, and an AI dot with your model name |
| 1.3 | In the Webex Assistant space, type`/help`  | A reply (with the 🤖 header) listing what the assistant can do and the quick commands                                                                              |
| 1.4 | Look at the web page's**Assistant** tab    | The same messages appear there too: yours tagged "via Webex", the assistant's in their own bubbles (no header needed there)                                        |
| 1.5 | Type`show my rules`                        | "You don't have any rules yet. Try: …". The web page's**Rules** tab is empty too                                                                                   |

- [ ] 1.1 · [ ] 1.2 · [ ] 1.3 · [ ] 1.4 · [ ] 1.5

---

## 2. Focus mode on/off

| #   | Do                                          | You should see                                                                                                                                                   |
| --- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2.1 | Webex Assistant space:`/focus on`           | "🎯 Focus is ON…". The web page's top bar turns**Focus ON** with a timer, without a reload                                                                       |
| 2.2 | `/status`                                   | "Focus is ON since HH:MM (…). So far: 0 high priority, 0 waiting"                                                                                                |
| 2.3 | Web page: click**End focus** in the top bar | Top bar shows Focus OFF. In Webex, "✅ Focus is OFF…", then a few seconds later "📋 Here's what you missed…" (it says "Nothing to summarize" if nothing came in) |
| 2.4 | Chat:`start focusing` (plain words)         | Focus ON again via the AI. Leave it on for section 3                                                                                                             |

- [ ] 2.1 · [ ] 2.2 · [ ] 2.3 · [ ] 2.4

---

## 3. Before any rules: defaults + AI (focus ON)

No rules yet, so B is not special: the AI judges B like anyone else.

| #   | Who / where                   | Message                                        | Expected                                                                                            |
| --- | ----------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 3.1 | **B** in A↔B (1:1)            | `lunch at 12?`                                 | **No alert.** Triage tab: **Regular** with an **AI** tag, reason like `ai: casual lunch invitation` |
| 3.2 | **C** in A↔C (1:1)            | `prod is down for EU customers, can you look?` | **Alert.** **High** with an **AI** tag, reason like `ai: reports a production outage`               |
| 3.3 | **C** in Team (no mention)    | `anyone seen the new coffee machine?`          | **No alert.** Regular (AI)                                                                          |
| 3.4 | **C** in Team, **@mention A** | `@A can you check the build?`                  | **Alert** ("C mentioned you in Team"). High, reason `default:mention`. Triage row shows "@you"      |
| 3.5 | **C** in Team, **@All**       | `@All standup moved to 10:30`                  | **Alert.** High, `default:mention` (@All counts as a mention)                                       |
| 3.6 | **A** replies in A↔B          | `sure, 12 works`                               | No alert, and**not** in Triage (your own messages are only kept for summaries)                      |
| 3.7 | **C** in A↔C                  | `He said "it's done" & left \o/`               | In Triage the text shows exactly as typed (whichever category the AI picks)                         |

- [ ] 3.1 · [ ] 3.2 · [ ] 3.3 · [ ] 3.4 · [ ] 3.5 · [ ] 3.6 · [ ] 3.7

---

## 4. Create your rules by chatting

Type these in the **Webex Assistant** space (or the web page's Assistant tab; both show the same conversation). Keep the web page's **Rules** tab open in another window: each new rule appears there.

| #   | A types                                             | Expected                                                                                                                                                           |
| --- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 4.1 | `notify me when <B's first name> writes`            | It looks B up (B has messaged A, so B is known) and replies "✅ Added rule #1: messages from**<B's email>** → 🔔 High priority. It applies from the next message." |
| 4.2 | `anything with the word urgent is important`        | "✅ Added rule #2: messages containing "**urgent**" → 🔔 High priority…"                                                                                           |
| 4.3 | `anything in Team can wait`                         | "✅ Added rule #3: anything in**Team** → **Regular**…"                                                                                                             |
| 4.4 | `show my rules`                                     | The three rules in plain English. The web page shows rule cards with on/off switches                                                                               |
| 4.5 | `notify me when Zelda writes` (nobody by that name) | Says it can't find them and asks for an email.**No rule is added**                                                                                                 |
| 4.6 | `would I get pinged if C says "lunch?" in Team?`    | "That would be**Regular**… because rule#3 space=Team matches"                                                                                                      |
| 4.7 | `/rules`                                            | The same list, instantly (quick command, no AI)                                                                                                                    |

- [ ] 4.1 · [ ] 4.2 · [ ] 4.3 · [ ] 4.4 · [ ] 4.5 · [ ] 4.6 · [ ] 4.7

---

## 5. Triage with your rules (focus ON)

| #   | Who / where                                | Message                        | Expected                                                                                                                                         |
| --- | ------------------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 5.1 | **B** in A↔B                               | `lunch at 12?` (same as 3.1)   | **Alert** this time. High, reason `rule#1 sender=<B>`, "🔔 pinged". Your rule beats the AI                                                       |
| 5.2 | **B** in Team (no mention)                 | `FYI the release notes are up` | **Alert.** Both rule #1 (High) and rule #3 (Regular) match: **High wins**                                                                        |
| 5.3 | **C** in A↔C                               | `URGENT: please call me`       | **Alert.** High, `rule#2 keyword=urgent` (case doesn't matter)                                                                                   |
| 5.4 | **C** in Team                              | `urgent: the build is red`     | **Alert.** Keyword (High) beats the Team rule (Regular)                                                                                          |
| 5.5 | **C** in Team                              | `lunch anyone?`                | **No alert.** Regular, `rule#3 space=Team` (no AI involved: a rule matched)                                                                      |
| 5.6 | **C** in Team, **@mention A**              | `@A quick question`            | **No alert!** Regular, `rule#3 space=Team`. A matching rule beats the "@mention = High" default, so "Team can wait" also silences mentions there |
| 5.7 | Chat:`always notify me when I'm mentioned` | —                              | "✅ Added rule #4: when I'm**@mentioned** → 🔔 High priority"                                                                                    |
| 5.8 | **C** in Team, **@mention A**              | `@A another question`          | **Alert** now. Rule #4 (High) beats rule #3 (Regular)                                                                                            |
| 5.9 | **C** in A↔C                               | `cake in the kitchen 🎂`       | No alert. Regular (AI: no rule matches C in a 1:1)                                                                                               |

- [ ] 5.1 · [ ] 5.2 · [ ] 5.3 · [ ] 5.4 · [ ] 5.5 · [ ] 5.6 · [ ] 5.7 · [ ] 5.8 · [ ] 5.9

**Changing rules by chat**

| #    | A types                        | Expected                                                                                     |
| ---- | ------------------------------ | -------------------------------------------------------------------------------------------- |
| 5.10 | `pause the urgent rule`        | "⏸️ Rule #2 is paused…".**C** in A↔C: `urgent: still there?` → no keyword match (AI decides) |
| 5.11 | `turn the urgent rule back on` | "▶️ Rule #2 is back on…"                                                                     |
| 5.12 | `delete the Team rule`         | It**asks first**: "Delete rule #3 (…)? Reply yes to confirm." The rule still exists          |
| 5.13 | `yes`                          | "🗑️ Deleted rule #3".**C** in Team: `lunch anyone?` → the AI decides again (Regular)         |

- [ ] 5.10 · [ ] 5.11 · [ ] 5.12 · [ ] 5.13

**Focus OFF: everything is still sorted, nobody is pinged**

| #    | Do                                                      | Expected                                                                                                   |
| ---- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 5.14 | `/focus off`, then **B** sends `are you around?` in A↔B | **No alert.** Triage: **High** (not "🔔 pinged"). Details panel: "Focus was: Off", "You were notified: No" |
| 5.15 | `/focus on` again                                       | Top bar shows Focus ON                                                                                     |

- [ ] 5.14 · [ ] 5.15

**Restart safety** (polling catches up after downtime)

| #    | Do                                                                                      | Expected                                                                              |
| ---- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 5.16 | Stop Webex Focus (Ctrl+C).**C** sends `sent while you were away` in A↔C. Start it again | Within a few seconds the message appears in Triage. No duplicates of earlier messages |
| 5.17 | `show my rules`                                                                         | Your rules survived the restart                                                       |

- [ ] 5.16 · [ ] 5.17

**Quick commands** (instant, no AI needed; type them in the Webex Assistant space)

| #    | A types                                                                                                   | Expected                                                                                                                                                                         |
| ---- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5.18 | `/mode`                                                                                                   | "🎯 Focus is ON since …" (or OFF). Same as `/status`                                                                                                                             |
| 5.19 | `/mode off`, then `/mode on`                                                                              | OFF (+ the "what you missed" summary), then ON. The web page's top bar follows                                                                                                   |
| 5.20 | `/profile`                                                                                                | **What I pay attention to**: your focus profile text, **Watched keywords** ("urgent"), **Watched topics** (none yet), and "Learned from N corrections"                            |
| 5.21 | `/profile Production outages and direct requests from my manager are urgent. Questions from teammates can wait.` | "✅ Updated." followed by your sentence **word for word** (no AI rewording)                                                                                                       |
| 5.22 | `/profile explain`                                                                                        | The AI's reading in three groups: 🔔 **I'll interrupt you for**, 💤 **This can wait**, and 📚 **Learned from your corrections** (only if you've corrected anything)            |
| 5.23 | `/watch deploy`, then **C** in A↔C: `deploy finished`                                                     | "👀 Now watching the keyword "**deploy**"… (rule #N)". Then an **Alert**, reason `rule#N keyword=deploy`                                                                          |
| 5.24 | `/watch`                                                                                                  | Lists your keywords: "urgent" and "deploy"                                                                                                                                       |
| 5.25 | `/topic the budget`, then **C** in A↔C: `heads up, finance moved the budget review to Friday`             | "👀 Now watching the topic **the budget** (judged by AI)". Then an **Alert**, reason like `rule#N topic=the budget (ai)` (the word list doesn't need to match exactly)          |
| 5.26 | `/unwatch deploy`, then `/unwatch the budget`                                                             | "🗑️ Stopped watching …" for each. `/watch` now lists only "urgent"                                                                                                              |
| 5.27 | `/rule off 2`, then `/rule on 2`                                                                          | "⏸️ Rule #2 is paused…", then "▶️ Rule #2 is back on…"                                                                                                                           |
| 5.28 | `/mode sideways`                                                                                          | "I don't understand `/mode sideways`. Type `/help`…"                                                                                                                             |

- [ ] 5.18 · [ ] 5.19 · [ ] 5.20 · [ ] 5.21 · [ ] 5.22 · [ ] 5.23 · [ ] 5.24 · [ ] 5.25 · [ ] 5.26 · [ ] 5.27 · [ ] 5.28

---

## 6. Rules on the web page (Rules tab)

The same rules, managed with buttons instead of chat.

| #   | Do                                                                                                                            | Expected                                                                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6.1 | Rules tab                                                                                                                     | The rules you made by chat, in plain English, each with an on/off switch                                                                                                           |
| 6.2 | Add rule:**Regular** when **the space** is `Team` (pick it from the suggestions). Click **Preview on today's messages** first | Lists any of today's messages whose category would change (old → new), or "Wouldn't change any…". Messages matched by a High rule (B, "urgent", @mentions) stay High.**Save rule** |
| 6.3 | Add rule:**High** when **the text contains** `outage`. **C** in A↔C: `small outage on staging`                                | **Alert.** Reason `rule#… keyword=outage`                                                                                                                                          |
| 6.4 | **Try a message** box: sender = C's email, space `Team`, text `outage!`, click **Check**                                      | "High because rule#… keyword=outage" (High beats the Team rule). Nothing is sent                                                                                                   |
| 6.5 | Switch the**outage** rule off, then **Check** again                                                                           | Regular, because the Team rule now decides                                                                                                                                         |
| 6.6 | Triage tab: click C's`cake in the kitchen 🎂` → **Make a rule from this → Messages from C → High**                            | The Rules tab opens with the form pre-filled. Preview lists C's Regular messages that would become High.**Don't save** (or save, test, then delete it)                             |
| 6.7 | Add a rule with**the sender** = `Bob` (a name, not an email)                                                                  | Friendly error: a sender rule needs an email address                                                                                                                               |
| 6.8 | Delete the Team and outage rules (🗑, confirm). In chat:`show my rules`                                                       | Chat shows the same list as the page                                                                                                                                               |

- [ ] 6.1 · [ ] 6.2 · [ ] 6.3 · [ ] 6.4 · [ ] 6.5 · [ ] 6.6 · [ ] 6.7 · [ ] 6.8

---

## 7. Teaching and checking the AI

| #   | Do                                                                                                                                                             | Expected                                                                                                                                        |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 7.1 | Chat:`outages, customer escalations, and direct requests with a deadline today are urgent for me; social chat isn't` (or Rules tab → **Focus profile** → Save) | "✅ Updated. Your focus profile…" quoting it                                                                                                    |
| 7.2 | **C** in A↔C: `can you send me the budget numbers by 5pm today?`                                                                                               | Likely**High** (a direct request with a deadline), with an AI reason                                                                            |
| 7.3 | Chat:`C's last message was actually important` (or **not important**, if the AI already marked it High)                                                        | "👍 Got it: … should have been High priority". Triage shows "↑ Should be High" on that row                                                      |
| 7.4 | Triage tab → filter**Needs review**                                                                                                                            | Lists AI decisions you haven't reviewed. Click ✓ or ↑/↓ on each. The count drops and**Accuracy** updates (AI % shown separately)                |
| 7.5 | Chat:`how accurate was triage today?`                                                                                                                          | Counts, plus accuracy from your corrections                                                                                                     |
| 7.6 | Topic rule, by chat:`anything about the Q3 launch is important`. Then **C** in Team: `heads up, the Q3 launch timeline slipped a week`                         | A topic rule is added ("👀 Now watching the topic **the Q3 launch**…" or "✅ Added rule #N: anything about **the Q3 launch**…"), then an **Alert** with reason like `rule#… topic=the Q3 launch (ai)` |
| 7.7 | (Optional) Terminal:`python -m scripts.eval_triage`                                                                                                            | "AI triage accuracy: X/Y = Z%" plus the misses. Re-run it after editing the focus profile or`prompts/triage.md`                                 |

- [ ] 7.1 · [ ] 7.2 · [ ] 7.3 · [ ] 7.4 · [ ] 7.5 · [ ] 7.6 · [ ] 7.7

**Works without AI** (the demo fallback)

| #    | Do                                                                 | Expected                                                                              |
| ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| 7.8  | Stop Webex Focus, blank out`OPENAI_API_KEY` in `.env`, start again | Startup says "AI: not configured (slash commands only)" and "AI triage: off"          |
| 7.9  | Type`show my rules`                                                | "🤖 I can't reach the AI right now… The quick commands still work: …"                 |
| 7.10 | `/rules` · `/focus off` · `/focus on` · `/summary`                 | All work instantly                                                                    |
| 7.11 | **C** in A↔C: `prod is down` (no rule matches)                     | Regular, reason`default`: without AI, unmatched messages wait. Your rules still apply |
| 7.12 | Put the key back and restart                                       | AI answers again                                                                      |

- [ ] 7.8 · [ ] 7.9 · [ ] 7.10 · [ ] 7.11 · [ ] 7.12

---

## 8. Summaries any time (chat)

By now there's a mix of today's messages: High ones (B, urgent, mentions), Regular ones (C's chatter), and a couple of A's replies.

| #   | A types                                                      | Expected                                                                                                                                                                                                         |
| --- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 8.1 | `what did I miss?`                                           | A summary titled "Summary ·<today>, 00:00–now" with counts, a bold headline, **Highlights**, **Action items for you** (if anyone asked A for something), and **By space**. **Only Regular messages** are covered |
| 8.2 | `summarize everything today`                                 | Same layout, but it also covers High messages and**A's own replies** ("… sent by you" in the counts)                                                                                                             |
| 8.3 | `summarize yesterday` · `summarize Monday to today`          | The period in the title matches. If Webex Focus wasn't running back then: a note "No data before …"                                                                                                              |
| 8.4 | `/summary` · `/summary all` · `/summary focus`               | Held, everything, and the current/last focus session. Instant (no AI step to pick the tool)                                                                                                                      |
| 8.5 | Focus on →**C** sends 3 casual messages → `/focus off`       | "Focus is OFF", then (with the 🔔 header) "📋 Here's what you missed while you were focused:" covering**just those 3**                                                                                           |
| 8.6 | Focus on → immediately`/focus off`                           | "Nothing to summarize… 🎉"                                                                                                                                                                                       |
| 8.7 | `show my summaries` → `show summary <N>`                     | A list with kinds (Summary / While you were focused / End of day), then the full text of that one                                                                                                                |
| 8.8 | `email me that` (after a summary)                            | "✉️ Summary #N emailed to <A's email>. (For now it's saved as`data/outbox/….eml`…)"                                                                                                                              |
| 8.9 | Finder → open`data/outbox/` → double-click the newest `.eml` | It opens in Apple Mail as a formatted email (subject "Webex Focus · …")                                                                                                                                          |

- [ ] 8.1 · [ ] 8.2 · [ ] 8.3 · [ ] 8.4 · [ ] 8.5 · [ ] 8.6 · [ ] 8.7 · [ ] 8.8 · [ ] 8.9

---

## 9. Daily summary & email (optional, not needed for the demo)

The end-of-day summary runs by itself at **23:59** while Webex Focus is running. If the Mac was off or asleep, it catches up at the next start (up to 3 days back). Email is **mocked**: it's written to `data/outbox/`.

| #   | Do                                                                          | Expected                                                                                                                                                                    |
| --- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9.1 | Terminal:`python -m scripts.run_eod`                                        | Prints today's summary and "email written to data/outbox/….eml". The Webex Assistant space gets "🌙 End-of-day summary for …". Summaries tab: an**End of day** item with ✉️ |
| 9.2 | (Optional) Set`EOD_TIME` in `.env` to 2 minutes from now, restart, and wait | Same as 9.1, by itself. Terminal: "End-of-day summary scheduled daily at HH:MM"                                                                                             |
| 9.3 | (Optional) Leave Webex Focus stopped over midnight, then start it           | Yesterday's End of day summary appears shortly after start                                                                                                                  |

- [ ] 9.1 · [ ] 9.2 · [ ] 9.3

---

## 10. The web page, tab by tab

**Two ways to run these checks**

- **With your real accounts** (A, B, C): the most realistic. Steps that mention Webex need the listener running (`python -m listener`).
- **In the UI sandbox** (no Webex, fake people, your data untouched): fastest, and safe to hand to a teammate. Everything except the "Webex ↔ page" steps (10.3, 10.4, 10.10) works there. Edits on the Templates page go to a throwaway copy.

### UI sandbox (optional)

| #     | Do                                                                                                                | Expected                                                                                                                                                  |
| ----- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 10.S1 | Stop the real listener if it's running (both can run, but this avoids confusion). Run `python -m scripts.ui_sandbox` | "Webex Focus UI sandbox → http://localhost:8765". Open it: Focus ON, six messages in Triage from Bob, Carol, and Dana, 4 rules, one summary          |
| 10.S2 | Second terminal: `python -m scripts.ui_sandbox say carol "lunch anyone?" --space Team`                            | Prints `{'outcome': 'regular', …}`. Triage gets a new row at the top **without reloading**                                                               |
| 10.S3 | `python -m scripts.ui_sandbox say carol "can you check the build?" --space Team --mention`                         | `high`, reason `rule#2 mention`. The Assistant tab shows a 🔔 alert card. The top bar's high count goes up                                              |
| 10.S4 | `python -m scripts.ui_sandbox say dana "prod is down for EU customers!"`                                          | `high`, reason `ai: …` (with an OpenAI key; without one it's `regular`, `default`)                                                                       |
| 10.S5 | `python -m scripts.ui_sandbox say bob "can you review my PR?"`                                                    | `high`, reason `rule#1 sender=bob@example.com`                                                                                                            |
| 10.S6 | Now go through 10.1–10.34 below on `http://localhost:8765` (skip 10.3, 10.4, 10.10). Ctrl+C the sandbox when done | Everything is deleted on exit. Your real data and templates are unchanged                                                                                 |

- [ ] 10.S1 · [ ] 10.S2 · [ ] 10.S3 · [ ] 10.S4 · [ ] 10.S5 · [ ] 10.S6

### Top bar (always visible)

- [ ] 10.1 Shows Focus ON/OFF, "since HH:MM · duration · N high · N held", Start/End focus button, the polling dot ("Listening · 1s ago"), and the AI model
- [ ] 10.2 Stop Webex Focus → within ~10s the page says it can't reach the app. Start it again → recovers by itself

### 💬 Assistant

- [ ] 10.3 **Webex → page**: type `/status` in the Webex space. Within seconds it appears on the page ("via Webex") with the reply
- [ ] 10.4 **Page → Webex**: type `show my rules` on the page. In the Webex space, your message appears as a plain message from you, then the reply with the 🤖 header. The assistant answers **once** (no double reply)
- [ ] 10.5 While waiting for an answer, a "• • •" typing indicator shows
- [ ] 10.6 Alerts appear in the thread as 🔔 cards. Click **↑ High** / **↓ Regular** / ✓ on a card → the Triage tab reflects it
- [ ] 10.7 A rules reply shows rule cards. Flip a card's switch → the Rules tab shows it paused. Flip it back
- [ ] 10.8 A summary reply shows a 📋 card. **Open** goes to Summaries. **Email me** writes to the outbox
- [ ] 10.9 Quick buttons ("What did I miss?", "/mode", "/rules", "/profile", "/watch", …) send their text
- [ ] 10.10 Create a rule from the page's chat: `notify me when <C's first name> writes` → it appears in the Rules tab and in the Webex space's conversation. Delete it afterwards (`delete that rule` → `yes`)

### 🗂 Triage

- [ ] 10.11 With the page open, **C** sends a message → a new row appears at the top **without reloading** (briefly highlighted)
- [ ] 10.12 Filters **All / High / Regular / Needs review** show the right rows and counts. The search box filters by text
- [ ] 10.13 Change the date to yesterday → yesterday's messages. Today → back
- [ ] 10.14 Click a row → the details panel: full text, sender email, category, why, decided by (Rule / Default / AI), @mentioned, focus on/off at the time, notified yes/no
- [ ] 10.15 Mark a few rows (✓, ↑ High, ↓ Regular) → the verdict shows on the row, and "Reviewed N · Accuracy X%" updates
- [ ] 10.16 Your own messages never appear here

### ⚙ Rules

- [ ] 10.17 Start typing in the value box for **the sender** / **the space** → suggestions of people/spaces that have messaged A
- [ ] 10.18 Preview before saving (section 6.2). Save → appears in the list
- [ ] 10.19 Switch a rule off/on, delete one (asks to confirm)
- [ ] 10.20 "Try a message" box (section 6.4)
- [ ] 10.21 Focus profile shows what you set by chat in 7.1. Edit and save it here

### 📄 Summaries

- [ ] 10.22 The list shows each summary's kind (Summary / While you were focused / End of day), period, and ✉️ if emailed
- [ ] 10.23 **＋ New summary** → pick a date range and "What I missed" or "Everything" → Create → it opens when ready
- [ ] 10.24 **Regenerate** rewrites it (e.g. after more messages arrived in that period)
- [ ] 10.25 **Email me** → then **Open email preview ↗** shows the email in a new tab
- [ ] 10.26 **Copy** copies the text (paste it somewhere to check)
- [ ] 10.27 Kind filter (All kinds / On demand / Focus sessions / End of day) works

### ✏ Templates (for non-technical teammates)

- [ ] 10.28 The left list is grouped: Notifications, Chat replies, Summaries & email, AI instructions. Selecting one shows its text, its description, and clickable placeholders
- [ ] 10.29 Open `notify/assistant_post.md`, change `messaged you` to `wants you`. The preview updates as you type → **Save** → "Saved". **B** sends a 1:1 message → the alert in Webex uses the new words
- [ ] 10.30 Type `{{ sendr }}` → the preview shows "⚠️ {{ sendr }} isn't a known placeholder. Did you mean {{ sender }}?" and **Save is disabled**
- [ ] 10.31 **Reset to default** → the original text is back (and is used again)
- [ ] 10.32 Open `chat/space_post.md` (the header on the assistant's Webex messages). Change `🤖` to `💡` → Save → type `/status` in the Webex space → the reply starts with **💡 Webex Assistant**. Reset afterwards
- [ ] 10.33 Open `chat/rule_added.md`, change "It applies from the next message." to "Done! 🎉", Save → `notify me when <C's first name> writes` in chat → the confirmation ends with "Done! 🎉". Reset and delete the rule afterwards
- [ ] 10.34 Open `prompts/assistant.md` (purple note: only the AI reads it). Add `Always answer in a cheerful tone with one emoji.` → Save → ask `what did C say today?` → the tone changes. Reset afterwards

---

## 11. Claude Code / Copilot (optional)

The same tools are available from your IDE through the `webex-focus` MCP server.

- [ ] 11.1 Claude Code: `/mcp` → `webex-focus` connected (reconnect it after updating the code)
- [ ] 11.2 Ask: "show my Webex Focus rules", then "what did C send today?" → answers from the same data as the web page

---

## 12. Demo rehearsal

Run the script in [DEMO.md](DEMO.md) twice, each time starting from `python -m scripts.reset_demo` (no rules). Each run should take **under 7 minutes** with no fixes in between.

- [ ] Dry run 1 · [ ] Dry run 2

---

## Appendix A — Every capability, both ways

A checklist of **everything the assistant can do**, each one tried two ways: the **quick command** (instant, exact, works without AI) and **plain English** (the AI works out what you mean). Some things only exist one way; that's marked "—".

Run it any time after section 5, in the **Webex Assistant** space or the web page's Assistant tab. Use real names: "Carol" means C's first name, "Bob" means B's. Every plain-English phrase below was checked against the AI (`python -m scripts.eval_assistant`, 30/30 with gpt-4.1-mini). Re-run that script after changing `prompts/assistant.md` or the AI model.

**Focus mode**

| #   | Capability            | Quick command                  | Plain English (try)                                    | Expected                                                         |
| --- | --------------------- | ------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------------- |
| A.1 | Is focus on?          | `/mode` (or `/status`)         | `am I in focus mode?` · `how much have I missed?`      | "🎯 Focus is ON since … So far: N high, N waiting" (or OFF)      |
| A.2 | Turn focus on         | `/mode on` (or `/focus on`)    | `start focusing` · `I need to concentrate now`         | "🎯 Focus is ON…". Top bar turns ON                              |
| A.3 | Turn focus off        | `/mode off` (or `/focus off`)  | `I'm done focusing`                                    | "✅ Focus is OFF…", then the 🔔 "what you missed" summary       |

- [ ] A.1 quick · [ ] A.1 plain · [ ] A.2 quick · [ ] A.2 plain · [ ] A.3 quick · [ ] A.3 plain

**Rules**

| #    | Capability                    | Quick command                    | Plain English (try)                                                       | Expected                                                                                     |
| ---- | ----------------------------- | -------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| A.4  | List rules                    | `/rules`                         | `show my rules`                                                           | Plain-English list with rule numbers                                                         |
| A.5  | Add: a person is important    | —                                | `notify me when Carol writes`                                             | Looks Carol up, then "✅ Added rule #N: messages from **carol@…** → 🔔 High priority"        |
| A.6  | Add: a space can wait         | —                                | `anything in Team can wait`                                               | "✅ Added rule #N: anything in **Team** → **Regular**"                                       |
| A.7  | Add: @mentions always notify  | —                                | `always notify me when I'm mentioned`                                     | "✅ Added rule #N: when I'm **@mentioned** → 🔔 High priority" (or it's already there)       |
| A.8  | Pause a rule                  | `/rule off N`                    | `pause the urgent rule`                                                   | "⏸️ Rule #N is paused…"                                                                      |
| A.9  | Resume a rule                 | `/rule on N`                     | `turn the urgent rule back on`                                            | "▶️ Rule #N is back on…"                                                                     |
| A.10 | Delete a rule                 | `/rule delete N` (no confirm)    | `delete the Team rule` → it asks → `yes`                                  | "🗑️ Deleted rule #N…". Plain English asks first; the quick command doesn't                  |
| A.11 | Dry run ("would I be pinged?") | —                                | `would I get pinged if Carol says "server down" in Team?`                 | "That would be High/Regular, because …". Nothing is stored                                   |

- [ ] A.4 quick · [ ] A.4 plain · [ ] A.5 · [ ] A.6 · [ ] A.7 · [ ] A.8 quick · [ ] A.8 plain · [ ] A.9 quick · [ ] A.9 plain · [ ] A.10 quick · [ ] A.10 plain · [ ] A.11

**Keywords and topics you watch**

| #    | Capability                         | Quick command          | Plain English (try)                                 | Expected                                                                          |
| ---- | ---------------------------------- | ---------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------- |
| A.12 | Watch a keyword (exact text)       | `/watch deploy`        | `watch for the word deploy`                         | "👀 Now watching the keyword "**deploy**"…" (second time: "Already watching")     |
| A.13 | Watch a topic (judged by AI)       | `/topic the budget`    | `keep me posted on anything about the budget`       | "👀 Now watching the topic **the budget** (judged by AI)…"                        |
| A.14 | List what you watch                | `/watch`               | `what words am I watching?`                         | Your keywords 🔤 and topics 🧠 with rule numbers                                  |
| A.15 | Stop watching                      | `/unwatch deploy`      | `stop watching deploy`                              | "🗑️ Stopped watching "**deploy**"…". `/unwatch the budget` for the topic          |

- [ ] A.12 quick · [ ] A.12 plain · [ ] A.13 quick · [ ] A.13 plain · [ ] A.14 quick · [ ] A.14 plain · [ ] A.15 quick · [ ] A.15 plain

**What I pay attention to (focus profile)**

| #    | Capability                         | Quick command                 | Plain English (try)                                                                 | Expected                                                                                       |
| ---- | ---------------------------------- | ----------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| A.16 | Show it                            | `/profile`                    | `what am I paying attention to?`                                                    | Profile text, watched keywords and topics, "Learned from N corrections"                       |
| A.17 | Change it                          | `/profile <your words>`       | `only production outages are urgent for me; questions from teammates can wait`      | "✅ Updated…". Quick command: **word for word**. Plain English: the AI may tidy the wording   |
| A.18 | The AI's own reading               | `/profile explain`            | `what do you think is important to me?`                                             | 🔔 I'll interrupt you for … · 💤 This can wait … · 📚 Learned from your corrections (if any)   |

- [ ] A.16 quick · [ ] A.16 plain · [ ] A.17 quick · [ ] A.17 plain · [ ] A.18 quick · [ ] A.18 plain

**Messages, people, spaces, and corrections**

| #    | Capability                   | Quick command | Plain English (try)                                                 | Expected                                                                      |
| ---- | ---------------------------- | ------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| A.19 | Find messages                | —             | `what did Carol say today?` · `anything about the release today?`   | A list of matching messages with time, sender, space, and High/Regular        |
| A.20 | Look up a person             | —             | `what's Carol's email address?`                                     | "People matching "Carol": **Carol …** (carol@…)"                              |
| A.21 | Look up spaces               | —             | `which spaces have I been getting messages from?`                   | A list of spaces (1:1 chats and group spaces) with message counts             |
| A.22 | Correct a decision           | — (or ✓/↑/↓ in Triage) | `Carol's last message was actually important`              | "👍 Got it: … should have been High priority". Triage shows "↑ Should be High" |
| A.23 | Triage accuracy              | —             | `how accurate was triage today?`                                    | Counts, plus "You reviewed N: X% correct"                                     |

- [ ] A.19 · [ ] A.20 · [ ] A.21 · [ ] A.22 · [ ] A.23

**Summaries and email**

| #    | Capability                         | Quick command                       | Plain English (try)                                         | Expected                                                                       |
| ---- | ---------------------------------- | ----------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------ |
| A.24 | What I missed (Regular only)       | `/summary`                          | `what did I miss?`                                          | Summary with headline, highlights, action items, by space                      |
| A.25 | Everything (incl. my replies)      | `/summary all`                      | `summarize everything today` · `summarize Monday to today`  | Same layout; counts include "sent by you"                                      |
| A.26 | The last focus session             | `/summary focus`                    | —                                                           | "While you were focused · …"                                                   |
| A.27 | List saved summaries               | —                                   | `show my summaries`                                         | Numbered list with kinds (Summary / While you were focused / End of day)      |
| A.28 | Show one                           | —                                   | `show summary 1`                                            | That summary's full text                                                       |
| A.29 | Email one (mocked → outbox)        | —                                   | `email me summary 1` · `email me that`                      | "✉️ Summary #1 emailed to … (saved as `data/outbox/….eml`)"                   |

- [ ] A.24 quick · [ ] A.24 plain · [ ] A.25 quick · [ ] A.25 plain · [ ] A.26 · [ ] A.27 · [ ] A.28 · [ ] A.29

**Help**

| #    | Capability    | Quick command | Plain English (try)  | Expected                                                                  |
| ---- | ------------- | ------------- | -------------------- | ------------------------------------------------------------------------- |
| A.30 | What can you do? | `/help`    | `what can you do?`   | `/help`: the full list incl. every quick command. Plain English: a short answer from the AI |

- [ ] A.30 quick · [ ] A.30 plain

---

## Troubleshooting

| You see                                                                        | Likely cause → fix                                                                                              |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Startup: "No Webex space named 'Webex Assistant'"                              | Create it in Webex with exactly that name, or fix`ASSISTANT_SPACE_TITLE` in `.env` (0.2). Then restart          |
| You type in the Webex Assistant space and nothing answers                      | Check the terminal shows "Assistant space found". The title must match exactly (capitals and spaces too)        |
| `reset_demo` says "unrecognized arguments: --important"                        | That option is gone. Run`python -m scripts.reset_demo` with no arguments, then create rules by chat (section 4) |
| Login: "invalid_scope"                                                         | `WEBEX_SCOPES` asks for something not ticked on the integration (0.2)                                           |
| "Not logged in. Run: python -m scripts.login"                                  | Run it (as A)                                                                                                   |
| No desktop notification, but the 🔔 post shows up in the Webex Assistant space | macOS notification permission for Script Editor (0.3), or Focus/Do Not Disturb is on                            |
| Nothing arrives at all; top bar dot is red "Not polling"                       | Network/proxy. On the company network set`HTTPS_PROXY` and `SSL_CERT_FILE` in `.env`                            |
| Every unmatched message is "default", never "ai: …"                            | `OPENAI_API_KEY` missing or `AI_TRIAGE=off`. The startup line shows "AI triage: off"                            |
| "notify me when B writes" → "I couldn't find anyone…"                          | B hasn't messaged A since the reset. Have B send anything first, or give the email:`notify me when b@… writes`  |
| An @mention didn't alert                                                       | A Regular rule for that space matched (5.6). Add`always notify me when I'm mentioned`                           |
| Chat answers "I can't reach the AI right now (…)"                              | The reason in brackets says why (key, model name, quota, network). Slash commands still work                    |
| The assistant answers twice, or replies to its own posts                       | Shouldn't happen. Note what you typed and when, and check the terminal                                          |
| Web page shows "not built yet"                                                 | `cd ui && npm run build`, then restart                                                                          |
| Lots of`429` errors in the terminal                                            | Webex rate limit. Raise`POLL_INTERVAL` (e.g. 3)                                                                 |
