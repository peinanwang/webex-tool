# Phase 3 — Two categories & focus mode

Simplify the data model to the two categories from the requirements and add the focus on/off switch. No new external services: this phase reuses the polling listener and Priority bot relay that already exist, so it can be tested at home right away.

## Learn first
- **Schema migration**: changing the shape of existing tables. Because this is a POC, we rebuild the `messages` and `rules` tables (test data only) and **keep `kv`**, which holds the OAuth refresh token. Without it you would have to log in again.
- **Focus session**: one stretch of focus mode, from "on" to "off". Storing sessions lets Phase 7 summarize exactly "what you missed while focusing".

## Action items

### Data model (`shared/db.py`)
- [ ] `messages.status` → `messages.category` with `CHECK (category IN ('high', 'regular', 'self'))`
- [ ] New columns on `messages`: `decided_by` (`rule` / `default` / `ai` / `self`), `feedback` (NULL / `correct` / `should_be_high` / `should_be_regular`), `feedback_at`, `focus_on` (0/1 at arrival time), `notified_at` (rename of `relayed_at`)
- [ ] `rules.action` → `rules.category` with `CHECK (category IN ('high', 'regular'))`
- [ ] New table `focus_sessions (id, started_at, ended_at, summary_id)`
- [ ] `python -m shared.db --migrate-v2`: drops and recreates `messages` + `rules`, keeps `kv`, prints what it did
- [ ] Update helpers: `query_messages(categories=…)`, `count_by_category`, `set_feedback(message_id, label)`

### Rules engine (`shared/rules.py`)
- [ ] Categories `high` / `regular`. Precedence **high > regular**, ties → oldest rule
- [ ] Defaults when nothing matched: @mention → `high` (`default:mention`), otherwise `regular` (`default`)
- [ ] Return `(category, reason, decided_by)`
- [ ] Update `tests/test_rules.py`: precedence, defaults, disabled rules, and a regular space rule silencing an @mention unless a `high mention` rule exists
- [ ] `scripts/seed_rules.py`: `--important EMAIL` (high sender), `--keyword` (high), `--regular-space TITLE`, `--reset`. Always seeds `high mention`

### Focus mode (`shared/focus.py`)
- [ ] `status()`, `turn_on()`, `turn_off()`. State lives in `kv` (`focus_mode`, `focus_session_id`). `turn_off()` closes the session and returns it (Phase 7 hooks the summary in here)
- [ ] Turning it on twice or off twice is harmless (returns the current state)
- [ ] CLI for testing before the chat exists: `python -m shared.focus on|off|status`

### Pipeline (`listener/pipeline.py`)
- [ ] Always categorize and store. Set `focus_on` from the current focus state
- [ ] Notify only when `category == 'high'` **and** focus is on
- [ ] Remove every `ignore` code path (pipeline, MCP tools, digest input)
- [ ] `POLL_INTERVAL` accepts decimals (e.g. `0.5`). The default becomes `2`
- [ ] Set `LISTENER_MODE=polling` as the default in `.env.example`

## Checkpoint
- [ ] `pytest` passes
- [ ] `python -m shared.db --migrate-v2`, then `python -m scripts.login` is **not** needed (token survived)
- [ ] `python -m shared.focus on` → B messages A → row is `high`, `rule#N sender=…`, and the bot pings
- [ ] C messages A → row is `regular`, no ping
- [ ] `python -m shared.focus off` → B messages A → row is `high` with `focus_on=0`, no ping
- [ ] `sqlite3 data/focus.db "SELECT * FROM focus_sessions"` shows one closed session
