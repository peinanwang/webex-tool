"""Unit tests for the rules engine. Run: pytest"""

from shared.rules import evaluate


def rule(id, action, match_type, value="", enabled=1):
    return {"id": id, "action": action, "match_type": match_type, "value": value, "enabled": enabled}


def msg(email="c@x.com", room="Team Chat", text="hello", mentioned=False):
    return {"person_email": email, "room_title": room, "room_id": "room-1", "text": text,
            "mentioned_me": int(mentioned)}


B = rule(1, "notify", "sender", "b@x.com")
URGENT = rule(2, "notify", "keyword", "urgent")
IGNORE_RANDOM = rule(3, "ignore", "space", "Random")
DIGEST_TEAM = rule(4, "digest", "space", "Team Chat")
MENTION = rule(5, "notify", "mention")


def test_unmatched_defaults_to_digest():
    assert evaluate(msg(), []) == ("digest", "default")


def test_mention_defaults_to_notify():
    assert evaluate(msg(mentioned=True), []) == ("notify", "default:mention")


def test_sender_rule_notifies():
    assert evaluate(msg(email="b@x.com"), [B]) == ("notify", "rule#1 sender=b@x.com")


def test_sender_match_ignores_case():
    assert evaluate(msg(email="B@X.com"), [B])[0] == "notify"


def test_keyword_is_case_insensitive_substring():
    assert evaluate(msg(text="URGENT: server down"), [URGENT]) == ("notify", "rule#2 keyword=urgent")


def test_ignore_beats_notify():
    m = msg(email="b@x.com", room="Random", text="urgent!!")
    assert evaluate(m, [B, URGENT, IGNORE_RANDOM]) == ("ignore", "rule#3 space=Random")


def test_notify_beats_digest():
    m = msg(email="b@x.com", room="Team Chat")
    assert evaluate(m, [DIGEST_TEAM, B]) == ("notify", "rule#1 sender=b@x.com")


def test_rule_beats_mention_default():
    # A digest rule matched, so the mention default doesn't apply...
    m = msg(room="Team Chat", mentioned=True)
    assert evaluate(m, [DIGEST_TEAM]) == ("digest", "rule#4 space=Team Chat")


def test_explicit_mention_rule_keeps_mentions_loud():
    # ...unless there's an explicit notify-mention rule, which beats digest.
    m = msg(room="Team Chat", mentioned=True)
    assert evaluate(m, [DIGEST_TEAM, MENTION]) == ("notify", "rule#5 mention")


def test_disabled_rule_is_skipped():
    assert evaluate(msg(email="b@x.com"), [rule(1, "notify", "sender", "b@x.com", enabled=0)]) == ("digest", "default")


def test_tie_goes_to_oldest_rule():
    m = msg(email="b@x.com", text="urgent")
    assert evaluate(m, [URGENT, B])[1] == "rule#1 sender=b@x.com"


def test_space_matches_room_id_too():
    assert evaluate(msg(), [rule(6, "ignore", "space", "room-1")])[0] == "ignore"
