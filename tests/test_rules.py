"""Unit tests for the rules engine. Run: pytest"""

from shared.rules import evaluate


def rule(id, category, match_type, value="", enabled=1):
    return {"id": id, "category": category, "match_type": match_type, "value": value, "enabled": enabled}


def msg(email="c@x.com", room="Team Chat", text="hello", mentioned=False):
    return {"person_email": email, "room_title": room, "room_id": "room-1", "text": text,
            "mentioned_me": int(mentioned)}


B = rule(1, "high", "sender", "b@x.com")
URGENT = rule(2, "high", "keyword", "urgent")
REGULAR_RANDOM = rule(3, "regular", "space", "Random")
REGULAR_TEAM = rule(4, "regular", "space", "Team Chat")
MENTION = rule(5, "high", "mention")


def test_unmatched_defaults_to_regular():
    assert evaluate(msg(), []) == ("regular", "default", "default")


def test_mention_defaults_to_high():
    assert evaluate(msg(mentioned=True), []) == ("high", "default:mention", "default")


def test_sender_rule_is_high():
    assert evaluate(msg(email="b@x.com"), [B]) == ("high", "rule#1 sender=b@x.com", "rule")


def test_sender_match_ignores_case():
    assert evaluate(msg(email="B@X.com"), [B])[0] == "high"


def test_keyword_is_case_insensitive_substring():
    assert evaluate(msg(text="URGENT: server down"), [URGENT]) == ("high", "rule#2 keyword=urgent", "rule")


def test_high_beats_regular():
    # B writes "urgent" in a regular space: missing it costs more than an extra ping.
    m = msg(email="b@x.com", room="Random", text="urgent!!")
    assert evaluate(m, [REGULAR_RANDOM, B, URGENT]) == ("high", "rule#1 sender=b@x.com", "rule")


def test_regular_rule_alone_wins():
    assert evaluate(msg(room="Random"), [REGULAR_RANDOM]) == ("regular", "rule#3 space=Random", "rule")


def test_rule_beats_mention_default():
    # A regular rule matched, so the mention default doesn't apply...
    m = msg(room="Team Chat", mentioned=True)
    assert evaluate(m, [REGULAR_TEAM]) == ("regular", "rule#4 space=Team Chat", "rule")


def test_explicit_mention_rule_keeps_mentions_loud():
    # ...unless there's an explicit high-mention rule, which beats regular.
    m = msg(room="Team Chat", mentioned=True)
    assert evaluate(m, [REGULAR_TEAM, MENTION]) == ("high", "rule#5 mention", "rule")


def test_disabled_rule_is_skipped():
    disabled = rule(1, "high", "sender", "b@x.com", enabled=0)
    assert evaluate(msg(email="b@x.com"), [disabled]) == ("regular", "default", "default")


def test_tie_goes_to_oldest_rule():
    m = msg(email="b@x.com", text="urgent")
    assert evaluate(m, [URGENT, B])[1] == "rule#1 sender=b@x.com"


def test_space_matches_room_id_too():
    assert evaluate(msg(), [rule(6, "regular", "space", "room-1")])[0] == "regular"
