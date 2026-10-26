"""AI triage: decide high vs. regular for a message that no rule matched.

Inputs to the model (prompt: templates/prompts/triage.md):
- A's focus profile: plain-language "what matters to me" (kv `focus_profile`).
- A's corrections from the Triage tab, as examples ("A said this one should be High").
- A's `topic` rules ("anything about the Q3 launch"), which only the AI can judge.

Rules always run first and the AI never overrides them. If the LLM is slow or down, classify()
returns None and the message falls back to the default (regular), so triage never blocks.
"""

import json

from shared import config, db, llm
from shared.log import log
from shared.rules import describe
from shared.templates import render

DEFAULT_PROFILE = (
    "Urgent: production incidents and outages, direct questions or requests addressed to me, "
    "anything with a deadline today, and messages from my manager. "
    "Not urgent: social chat, FYIs, newsletters, and general announcements."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ["high", "regular"],
                     "description": "high = interrupt the user now; regular = it can wait for the summary"},
        "reason": {"type": "string", "description": "Why, in at most 10 words, e.g. 'reports a production outage'"},
        "topic_rule_id": {"type": "integer",
                          "description": "id of the topic rule this message is about, or 0 if none"},
    },
    "required": ["category", "reason", "topic_rule_id"],
}


def get_profile() -> str:
    return db.kv_get("focus_profile") or DEFAULT_PROFILE


def set_profile(text: str) -> str:
    db.kv_set("focus_profile", text.strip())
    return get_profile()


def enabled() -> bool:
    return config.AI_TRIAGE and llm.is_configured()


def _example(row: dict) -> dict:
    return {"sender": row.get("person_name") or row.get("person_email"), "space": row.get("room_title"),
            "text": (row.get("text") or "")[:300], "label": row["label"]}


def classify(message: dict, profile: str | None = None, examples: list[dict] | None = None,
             topic_rules: list[dict] | None = None) -> tuple[str, str, str] | None:
    """Return (category, reason, decided_by) or None if the AI couldn't decide in time."""
    profile = profile or get_profile()
    examples = [_example(r) for r in (examples if examples is not None else db.labeled_examples(10))]
    topics = topic_rules if topic_rules is not None else [
        r for r in db.list_rules(enabled_only=True) if r["match_type"] == "topic"]
    system = render("prompts/triage.md", profile=profile, examples=examples,
                    topics=[{"id": r["id"], "topic": r["value"], "category": r["category"]} for r in topics])
    user = json.dumps({
        "sender": message.get("person_name") or message.get("person_email"),
        "space": message.get("room_title"),
        "space_type": "1:1 direct message" if message.get("room_type") == "direct" else "group space",
        "mentions_me": bool(message.get("mentioned_me")),
        "text": (message.get("text") or "")[:2000],
    }, ensure_ascii=False)
    try:
        result = llm.extract(system, user, "submit_triage", "Record the triage decision for this message.",
                             SCHEMA, model=config.TRIAGE_MODEL, timeout=config.TRIAGE_TIMEOUT)
    except llm.LLMUnavailable as exc:
        log(f"[triage-ai] skipped ({exc}); using the default")
        return None

    rule = next((r for r in topics if r["id"] == result.get("topic_rule_id")), None)
    if rule:  # a topic rule applies: its category wins, like any other rule
        return rule["category"], f"{describe(rule)} (ai)", "ai"
    category = result.get("category") if result.get("category") in db.CATEGORIES else "regular"
    reason = " ".join(str(result.get("reason") or "no reason given").split()[:12])
    return category, f"ai: {reason}", "ai"


# --- "/profile explain": the AI's own reading of what matters to A ---

EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "urgent": {"type": "array", "items": {"type": "string"},
                   "description": "3-6 short bullets: what interrupts the user (High)"},
        "can_wait": {"type": "array", "items": {"type": "string"},
                     "description": "2-5 short bullets: what waits for the summary (Regular)"},
        "learned": {"type": "array", "items": {"type": "string"},
                    "description": "0-4 short bullets: patterns learned from the user's corrections; empty if none"},
    },
    "required": ["urgent", "can_wait", "learned"],
}


def explain() -> dict | None:
    """Ask the AI to sum up what it treats as urgent for A. Returns None if the AI is unavailable."""
    rules = [{"category": r["category"], "match_type": r["match_type"], "value": r["value"]}
             for r in db.list_rules(enabled_only=True)]
    system = render("prompts/explain_profile.md", profile=get_profile(), rules=rules,
                    examples=[_example(r) for r in db.labeled_examples(20)])
    try:
        return llm.extract(system, "Explain how you decide what is urgent for me.", "submit_explanation",
                           "Record your explanation of the user's priorities.", EXPLAIN_SCHEMA)
    except llm.LLMUnavailable as exc:
        log(f"[triage-ai] explain skipped ({exc})")
        return None

