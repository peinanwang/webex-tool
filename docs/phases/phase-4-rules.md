# Phase 4 — Rules engine & Priority bot relay

Decide what happens to each message and relay the important ones through the Priority bot.

## Rules semantics (from CLAUDE.md)
- Actions: `notify` | `digest` | `ignore`
- Match on: `sender` (email), `space` (room title or id), `keyword` (case-insensitive substring), `mention` (A is @mentioned)
- Precedence when several rules match: **ignore > notify > digest**
- Defaults: @mention of A → notify; unmatched → digest

## Action items
- [ ] `shared/rules.py`:
  - [ ] `evaluate(message, rules) -> (action, reason)`. `reason` names the rule that fired, e.g. `rule#3 sender=b@…` or `default:mention`
  - [ ] Pure function with no DB or network calls, so it's easy to test
- [ ] DB helpers in `shared/db.py`: `list_rules()`, `add_rule()`, `delete_rule()`, `set_rule_enabled()`
- [ ] Seed script `scripts/seed_rules.py`: notify for sender B, a keyword rule (e.g. "urgent"), and an ignore example
- [ ] Listener: call `evaluate()` before inserting; store `status` and `reason` (A's own messages stay `self` and never reach `evaluate()`)
- [ ] Relay for `notify`: bot sends A a 1:1 like
  `🔔 **B** in *Team Chat*: message text` with the reason in small text; set `relayed_at`
- [ ] `ignore`: store it with `status='ignore'` (still logged, but left out of the digest)
- [ ] Unit tests `tests/test_rules.py` for precedence and defaults (pytest)

## Checkpoint
- [ ] `pytest` passes
- [ ] B messages A → the Priority bot relays it within a few seconds
- [ ] C messages A → no relay; row is `digest`
- [ ] C @mentions A in the group → relayed (`default:mention`)
- [ ] C says "urgent" → relayed (keyword rule)
- [ ] Every row has a non-empty `reason`
- [ ] A messages B in a space with a keyword rule → stored as `self`, not relayed
