# Phase 3 — Two categories & focus mode

**Status: built 2026-10-26** (automated tests pass). Hands-on checks: [VERIFY.md](../VERIFY.md).

Simplify the data model to the two categories from the requirements and add the focus on/off switch. No new external services: this phase reuses the polling listener and Priority bot relay that already exist, so it can be tested at home right away.

## Learn first
- **Schema migration**: changing the shape of existing tables. SQLite can't change a column's allowed values in place, so we rename the old table, create the v2 one, copy the rows over (converting `notify` → `high`, `digest`/`ignore` → `regular`), and drop the old table, all in one transaction. `kv` (the OAuth refresh token) is never touched. `init_db()` does this automatically the first time it sees a v1 table, so no process ever runs against a half-old schema.
- **Focus session**: one stretch of focus mode, from "on" to "off". Storing sessions lets Phase 7 summarize exactly "what you missed while focusing".

## Action items

### Data model (`shared/db.py`)
- [x] `messages.status` → `messages.category` with `CHECK (category IN ('high', 'regular', 'self'))`
- [x] New columns on `messages`: `decided_by` (`rule` / `default` / `ai` / `self`), `feedback` (NULL / `correct` / `should_be_high` / `should_be_regular`), `feedback_at`, `focus_on` (0/1 at arrival time), `notified_at` (rename of `relayed_at`)
- [x] `rules.action` → `rules.category` with `CHECK (category IN ('high', 'regular'))`
- [x] New table `focus_sessions (id, started_at, ended_at, summary_id)`
- [x] Automatic v1 → v2 upgrade in `init_db()`: converts `messages` + `rules` (keeps rule ids, since reasons refer to them), keeps `kv`. `python -m shared.db` prints what it upgraded
- [x] Update helpers: `query_messages(categories=…)`, `count_by_category`, `set_feedback(message_id, label)`

### Rules engine (`shared/rules.py`)
- [x] Categories `high` / `regular`. Precedence **high > regular**, ties → oldest rule
- [x] Defaults when nothing matched: @mention → `high` (`default:mention`), otherwise `regular` (`default`)
- [x] Return `(category, reason, decided_by)`
- [x] Update `tests/test_rules.py`: precedence, defaults, disabled rules, and a regular space rule silencing an @mention unless a `high mention` rule exists
- [x] `scripts/seed_rules.py`: `--important EMAIL` (high sender), `--keyword` (high), `--regular-space TITLE`, `--reset`. Always seeds `high mention` (optional helper; since 2026-10-26 the demo starts with no rules, see `scripts/reset_demo.py`)

### Focus mode (`shared/focus.py`)
- [x] Focus starts **off** on a fresh install (the listener prints the current state at startup)
- [x] `status()`, `turn_on()`, `turn_off()`. State lives in `kv` (`focus_mode`, `focus_session_id`). `turn_off()` closes the session and returns it (Phase 7 hooks the summary in here)
- [x] Turning it on twice or off twice is harmless (returns the current state)
- [x] CLI for testing before the chat exists: `python -m shared.focus on|off|status`

### Pipeline (`listener/pipeline.py`)
- [x] Always categorize and store. Set `focus_on` from the current focus state
- [x] Notify only when `category == 'high'` **and** focus is on
- [x] Remove every `ignore` code path (pipeline, MCP tools, digest input). MCP tools use `category` now; Phase 5 rewrites them
- [x] `POLL_INTERVAL` accepts decimals (e.g. `0.5`). The default becomes `2`
- [x] Set `LISTENER_MODE=polling` as the default in `.env.example`

## Checkpoint
- [x] `pytest` passes (23 tests: rules, migration, feedback, focus, pipeline notify decision)
- [ ] `python -m shared.db` prints "Upgraded from v1: messages, rules", then `python -m shared.webex_client` still works (no re-login)
- [ ] `python -m shared.focus on` → B messages A → row is `high`, `rule#N sender=…`, and the bot pings
- [ ] C messages A → row is `regular`, no ping
- [ ] `python -m shared.focus off` → B messages A → row is `high` with `focus_on=0`, no ping
- [ ] `sqlite3 data/focus.db "SELECT * FROM focus_sessions"` shows one closed session
