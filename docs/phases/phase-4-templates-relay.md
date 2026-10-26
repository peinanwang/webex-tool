# Phase 4 — Templates & relay through the integration

Make the alert path work on the company network: no bot, no ngrok. Also introduce templates, because the first user-facing text (the alert) is written in this phase.

## Learn first
- **Templates (Jinja2)**: a text file with placeholders, like `🔔 **{{ sender }}** in {{ space }}`. Code passes in the values, and the template decides the wording and layout. A non-technical teammate can change the wording without touching Python. `{% if %}` and `{% for %}` exist for the rare case that needs logic.
- **Why integration posts don't alert you**: the integration acts *as A*. Webex never notifies you about your own messages. So the post in the Focus Assistant space is the record, and a **desktop notification** from our Python process is the actual alert. (The hackathon used the same workaround. Its code isn't available, so we build it here.)
- **Our own posts come back through polling**: everything we post into the Focus Assistant space shows up as a new message from A. We record each id in `app_posts` and skip those messages, otherwise we'd loop.

## Action items

### Template engine
- [ ] `requirements.txt`: add `jinja2`, `pyyaml`
- [ ] `shared/templates.py`: `render(name, **values) -> str`
  - [ ] Reads from `templates/` on every call (edits apply without a restart)
  - [ ] `StrictUndefined`: a misspelled placeholder is an error, not silent blank text
  - [ ] `SandboxedEnvironment`, so template files can't run arbitrary code
- [ ] File header convention: every template starts with a `{# … #}` comment saying when it's used and which placeholders exist
- [ ] `templates/samples.yaml`: sample values for every template (used by tests now, and by the Phase 11 preview)
- [ ] `tests/test_templates.py`: renders every template with its sample data (catches broken edits)
- [ ] `templates/README.md`: a one-page guide for non-technical teammates (what each folder is, how placeholders work, how to test)
- [ ] First templates: `notify/assistant_post.md`, `notify/desktop_title.txt`, `notify/desktop_body.txt`

### Focus Assistant space
- [ ] Add the `spark:rooms_write` scope to the integration on developer.webex.com and to `SCOPES` in `shared/webex_client.py`. Re-run `python -m scripts.login` (creating a space needs it)
- [ ] `webex_client.user_send(markdown, room_id)`: posts as A and records the new message id in `app_posts`
- [ ] New table `app_posts (webex_message_id PRIMARY KEY, created_at)`
- [ ] `scripts/setup_assistant_space.py` (also run automatically at listener startup): find the space titled `ASSISTANT_SPACE_TITLE` (default "Focus Assistant") that A created, or create it. Save `assistant_room_id` in `kv`
- [ ] Pipeline: skip ids in `app_posts`. Messages from A in the assistant space are **not** triaged (Phase 6 routes them to the agent; for now, just log them)

### Notifier (`shared/notifier.py`)
- [ ] `notify(row)` sends to each channel in `NOTIFY_CHANNELS` (e.g. `assistant_space,desktop`). One channel failing doesn't stop the others. Sets `notified_at`
- [ ] `assistant_space`: `user_send(render("notify/assistant_post.md", …))`
- [ ] `bot`: the existing Priority bot relay (home setup only)
- [ ] `.env.example`: `NOTIFY_CHANNELS` (default `assistant_space,desktop`, the same as the company setup, so home testing rehearses the real path), `ASSISTANT_SPACE_TITLE`, `DESKTOP_NOTIFIER`, `UI_URL`, and a comment explaining each channel

### Desktop notifications (`shared/desktop_notify.py`)
macOS is the demo machine, and Windows is supported. One function, `show(title, body, open_url=None)`. `DESKTOP_NOTIFIER=auto` picks a backend by `sys.platform`, or you can force one:
- [ ] **`terminal-notifier`** (macOS, preferred when installed: `brew install terminal-notifier`): supports `-open <url>`, so clicking the notification opens the UI on that message (`UI_URL/#/triage?msg=<id>`; before Phase 8, it opens Webex)
- [ ] **`osascript`** (macOS, built in, fallback): `display notification`. Pass the title and body as **arguments** (`on run argv`), never pasted into the script text, because message text from other people could otherwise break or inject AppleScript
- [ ] **`windows`**: `win11toast` (in `requirements.txt` with the marker `; sys_platform == "win32"`, so the Mac doesn't install it)
- [ ] **`off`**: logs only (for tests and CI)
- [ ] Bodies are truncated (~200 characters). A backend failure is logged and never stops the pipeline
- [ ] `python -m shared.desktop_notify "Test" "Hello from Webex Focus"` for a quick manual test
- [ ] Note for macOS: notifications from `osascript` are listed under **Script Editor** and from `terminal-notifier` under **terminal-notifier** in System Settings → Notifications. Allow them there, and check that Focus / Do Not Disturb isn't hiding them

## Checkpoint
- [ ] `pytest` passes, including the template render test
- [ ] Listener startup prints "Focus Assistant space: <id>", and the space exists in Webex
- [ ] `python -m shared.desktop_notify "Test" "Hello"` shows a macOS notification (try both `terminal-notifier` and `osascript`)
- [ ] `NOTIFY_CHANNELS=assistant_space,desktop`, focus on → B messages A → a macOS notification appears, and a post shows up in the Focus Assistant space
- [ ] Clicking the notification (terminal-notifier) opens the link
- [ ] C sends a message containing quotes and backslashes (`"it's \"done\""`) under a `high` keyword rule → the notification shows it correctly (argument passing works)
- [ ] That post is **not** stored as a new message (check the `messages` table)
- [ ] Change the wording in `templates/notify/assistant_post.md` → the next alert uses it, with no restart
- [ ] Misspell a placeholder → `pytest` fails with a clear message naming the template
- [ ] (When a Windows machine is available) `DESKTOP_NOTIFIER=windows` shows a toast
