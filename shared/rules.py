"""Decide what happens to a message: notify, digest, or ignore.

Order (see CLAUDE.md "Rules semantics"):
1. Collect every enabled rule that matches.
2. If any matched, the strongest action wins: ignore > notify > digest.
   Ties go to the oldest rule (lowest id), so the reason is stable.
3. If none matched: @mention of A → notify, otherwise → digest.

Rules always beat the defaults. To keep @mentions loud even inside a space with a digest rule,
add an explicit `notify mention` rule (scripts/seed_rules.py does).

This module is pure (no DB, no network) so it's easy to unit-test.
`message` is a dict with: person_email, room_title, room_id, text, mentioned_me.
"""

PRECEDENCE = {"ignore": 3, "notify": 2, "digest": 1}


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


def evaluate(message: dict, rules: list[dict]) -> tuple[str, str]:
    """Return (action, reason) for one message."""
    matched = [r for r in rules if r.get("enabled", 1) and rule_matches(r, message)]
    if matched:
        best = max(matched, key=lambda r: (PRECEDENCE[r["action"]], -r["id"]))
        return best["action"], describe(best)
    if message.get("mentioned_me"):
        return "notify", "default:mention"
    return "digest", "default"
