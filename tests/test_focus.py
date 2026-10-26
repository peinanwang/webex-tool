"""Focus mode, and the pipeline's routing and "notify only when high and focus on" decision. Run: pytest"""

import pytest

from listener import pipeline
from shared import db, focus


def test_starts_off(tmp_db):
    assert focus.status() == {"on": False, "session_id": None, "since": None, "counts": None}


def test_on_then_off_records_a_session(tmp_db):
    on = focus.turn_on()
    assert on["changed"] and on["on"] and on["counts"]["high"] == 0
    assert not focus.turn_on()["changed"]  # second "on" is harmless, same session
    assert focus.status()["session_id"] == on["session_id"]

    off = focus.turn_off()
    assert off["changed"] and off["session"]["ended_at"] >= off["session"]["started_at"]
    assert not focus.turn_off()["changed"]
    assert not focus.is_on()


def test_each_on_starts_a_new_session(tmp_db):
    first = focus.turn_on()["session_id"]
    focus.turn_off()
    assert focus.turn_on()["session_id"] == first + 1


# --- pipeline: no Webex calls; the full message is passed in and alerts are captured ---

@pytest.fixture
def pipe(tmp_db, monkeypatch):
    db.kv_set("my_person_id", "A")
    db.kv_set("assistant_room_id", "room-assistant")
    pipeline._room_cache.update({"room-1": {"title": "Bob Chen", "type": "direct"},
                                 "room-group": {"title": "Team Chat", "type": "group"}})
    pipeline._name_cache.update({"B": "Bob Chen", "C": "Carol Diaz", "A": "Alex"})
    alerts, chats = [], []
    monkeypatch.setattr(pipeline.notifier, "notify", lambda row: alerts.append(row["id"]) or ["desktop"])
    monkeypatch.setattr(pipeline.assistant, "on_user_message", lambda msg: chats.append(msg["text"]))
    db.add_rule("high", "sender", "b@x.com")
    return alerts, chats


def _webex_msg(id, person_id="B", email="b@x.com", room="room-1", text="hi", mentions=()):
    return {"id": id, "roomId": room, "roomType": "group" if room != "room-1" else "direct", "personId": person_id,
            "personEmail": email, "text": text, "created": "2026-10-26T10:00:00.000Z",
            "mentionedPeople": list(mentions)}


def test_high_message_notifies_only_when_focus_on(pipe):
    alerts, _ = pipe
    assert pipeline.process_message("m1", _webex_msg("m1")) == "high"
    assert alerts == []  # focus is off

    focus.turn_on()
    assert pipeline.process_message("m2", _webex_msg("m2")) == "high"
    assert alerts == ["m2"]

    rows = {r["id"]: r for r in db.query_messages()}
    assert (rows["m1"]["focus_on"], rows["m2"]["focus_on"]) == (0, 1)
    assert rows["m2"]["person_name"] == "Bob Chen"


def test_mention_in_a_group_space_is_high(pipe):
    alerts, _ = pipe
    focus.turn_on()
    msg = _webex_msg("m1", "C", "c@x.com", room="room-group", mentions=["A"])
    assert pipeline.process_message("m1", msg) == "high"
    assert db.get_message("m1")["reason"] == "default:mention"
    assert alerts == ["m1"]


def test_regular_and_self_never_notify(pipe):
    alerts, _ = pipe
    focus.turn_on()
    assert pipeline.process_message("m1", _webex_msg("m1", "C", "c@x.com")) == "regular"
    assert pipeline.process_message("m2", _webex_msg("m2", "A", "a@x.com")) == "self"
    assert alerts == []


def test_assistant_space_routing(pipe):
    _, chats = pipe
    assert pipeline.process_message("m1", _webex_msg("m1", "A", "a@x.com", room="room-assistant",
                                                     text="show my rules")) == "assistant"
    assert chats == ["show my rules"]
    assert not db.message_exists("m1")  # chat turns aren't triaged messages

    db.add_app_post("m2")  # something we posted ourselves
    assert pipeline.process_message("m2", _webex_msg("m2", "A", "a@x.com", room="room-assistant")) == "skipped:own-post"
    assert chats == ["show my rules"]


def test_ai_triage_decides_unmatched_messages(pipe, monkeypatch):
    monkeypatch.setattr(pipeline.triage_ai, "enabled", lambda: True)
    monkeypatch.setattr(pipeline.triage_ai, "classify", lambda row: ("high", "ai: reports an outage", "ai"))
    assert pipeline.process_message("m1", _webex_msg("m1", "C", "c@x.com", text="prod is down")) == "high"
    assert db.get_message("m1")["decided_by"] == "ai"
    # A matching rule always beats the AI:
    assert pipeline.process_message("m2", _webex_msg("m2")) == "high"
    assert db.get_message("m2")["decided_by"] == "rule"


def test_ai_unavailable_falls_back_to_default(pipe, monkeypatch):
    monkeypatch.setattr(pipeline.triage_ai, "enabled", lambda: True)
    monkeypatch.setattr(pipeline.triage_ai, "classify", lambda row: None)
    assert pipeline.process_message("m1", _webex_msg("m1", "C", "c@x.com")) == "regular"
    assert db.get_message("m1")["reason"] == "default"


# --- the Webex Assistant space ---

def test_space_posts_get_a_header_but_the_ui_thread_does_not(tmp_db, monkeypatch):
    from shared import assistant_space
    sent = []
    db.kv_set("assistant_room_id", "room-assistant")
    monkeypatch.setattr(assistant_space.wx, "user_send", lambda md, room: sent.append(md) or {"id": "w1"})
    row = assistant_space.post("✅ Added rule #1", role="assistant")
    assistant_space.post("🔔 Bob messaged you", role="notice")
    assert sent[0].startswith("🤖 **Webex Assistant**\n✅ Added rule #1")
    assert sent[1].startswith("🔔 **Webex Assistant**")
    assert db.list_chat()[0]["text"] == "✅ Added rule #1" and row["text"] == "✅ Added rule #1"
    assistant_space.mirror_user_text("show my rules")  # A's own words: no header
    assert sent[2] == "show my rules"


def test_space_is_found_by_title(tmp_db, monkeypatch):
    from shared import assistant_space
    db.kv_set("my_person_id", "A")
    rooms = [{"id": "r1", "title": "Webex Assistant", "creatorId": "X"},
             {"id": "r2", "title": "Webex Assistant", "creatorId": "A"},
             {"id": "r3", "title": "Team", "creatorId": "A"}]
    monkeypatch.setattr(assistant_space.wx, "list_group_rooms", lambda: rooms)
    assert assistant_space.find_space() == "r2"  # the one A created wins
    monkeypatch.setattr(assistant_space.wx, "list_group_rooms", lambda: rooms[2:])
    with pytest.raises(assistant_space.SpaceNotFound, match="create a space"):
        assistant_space.find_space()
    assert assistant_space.room_id() is None
