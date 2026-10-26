# Demo script (about 7 minutes)

The demo starts with **no rules**. The audience watches the AI sort messages, then you set your rules by chatting.

**Before the audience arrives**
1. `python -m scripts.reset_demo --clear-outbox`. Afterwards there are no rules, focus is off, and history is empty.
2. Have **B** send A one message (e.g. `morning!`) so the assistant knows B by name. Optional: `python -m scripts.run_eod` the evening before, so there's an "End of day" summary and email to show in step 10.
3. `python -m listener`. Then open `http://localhost:8000` on the Assistant tab.
4. Webex as A: A↔B, A↔C, and Team are muted. Mac: Do Not Disturb off.
5. Have B's and C's messages ready to paste (below). Run B and C on a phone or a second browser profile.

| #   | Show                                                                                                                         | Say                                                                                                           |
| --- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 1   | Web page top bar → **Start focus**. Rules tab: empty                                                                         | "I'm going heads-down. I haven't set up any rules yet."                                                       |
| 2   | **C** sends `lunch at 12?` and `cake in the kitchen 🎂`. **C** sends `prod is down for EU customers!`. Switch to **Triage** | "No rules, so the AI judges each message against what I said matters. Chatter waits; the outage pinged me."  |
| 3   | Webex, Webex Assistant space: `notify me when <B's first name> writes`                                                       | The rule is added and shows on the Rules tab. "I set my rules in plain language, right inside Webex."        |
| 4   | Same chat: `anything in Team can wait` and `always notify me when I'm mentioned`                                             | Two more rules. "High always wins, so @mentions still get through in Team."                                  |
| 5   | **B** sends `Can you approve the release PR by 3pm?`                                                                         | Desktop alert + 🔔 in the Webex Assistant space. "That's my rule for B."                                      |
| 6   | **C** in Team: `who's bringing snacks?`, then **C** in Team: `@A can you check the build?`                                   | The first stays quiet (Team can wait). The @mention alerts                                                    |
| 7   | Triage: mark `cake in the kitchen` ✓ and the outage one ✓                                                                    | "My corrections teach the AI and give me an accuracy score."                                                  |
| 8   | Webex: `what did I miss?`                                                                                                    | The summary with highlights and action items. "Any time, any period."                                         |
| 9   | Webex: `/focus off`                                                                                                          | "Focus is OFF", then the automatic "what you missed while focused" summary                                    |
| 10  | **Summaries** tab → the End of day item → **Open email preview**                                                             | "Every night at 23:59 it emails me the day. Email is mocked in this POC."                                     |
| 11  | **Templates** → `notify/assistant_post.md`: change `messaged you` to `needs you`, Save. **B** sends `one more thing`        | The new wording appears. "Our non-technical teammates own the wording."                                      |

**If something fails:** the quick commands (`/focus on`, `/focus off`, `/rules`, `/summary`) work without the AI, and the Rules tab can add rules by hand. If the network dies, play the screen recording.
