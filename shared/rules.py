"""Decide a message's category: high (notify A now) or regular (hold for the summary).

Order (see CLAUDE.md "Triage semantics"):
1. Collect every enabled rule that matches.
2. If any matched, the strongest category wins: high > regular.
   Ties go to the oldest rule (lowest id), so the reason is stable.
3. If none matched: @mention of A → high, otherwise → regular.
   (Phase 10 adds AI triage between these two defaults; it lives in the pipeline, not here.)

Rules always beat the defaults. So a `regular` space rule silences @mentions in that space,
unless there's an explicit `high mention` rule (scripts/seed_rules.py adds one).

This module is pure (no DB, no network) so it's easy to unit-test.
`message` is a dict with: person_email, room_title, room_id, text, mentioned_me.
"""

PRECEDENCE = {"high": 2, "regular": 1}


def rule_matches(rule: dict, message: dict) -> bool:
    kind, value = rule["match_type"], (rule.get("value") or "").lower()
    if kind == "sender":
        return value == (message.get("person_email") or "").lower()
    if kind == "space":
        return value in ((message.get("room_title") or "").lower(), (message.get("room_id") or "").lower())
    if kind == "keyword":
        return value in (message.get("text") or "").lower()
    if kind == "mention":
        return bool(message.get("mentioned_me"))
    return False


def describe(rule: dict) -> str:
    """Short label stored as the message's `reason`, e.g. 'rule#3 sender=b@x.com'."""
    if rule["match_type"] == "mention":
        return f"rule#{rule['id']} mention"
    return f"rule#{rule['id']} {rule['match_type']}={rule['value']}"


def evaluate(message: dict, rules: list[dict]) -> tuple[str, str, str]:
    """Return (category, reason, decided_by) for one message. decided_by is 'rule' or 'default'."""
    matched = [r for r in rules if r.get("enabled", 1) and rule_matches(r, message)]
    if matched:
        best = max(matched, key=lambda r: (PRECEDENCE[r["category"]], -r["id"]))
        return best["category"], describe(best), "rule"
    if message.get("mentioned_me"):
        return "high", "default:mention", "default"
    return "regular", "default", "default"
