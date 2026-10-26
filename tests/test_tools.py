"""The tool registry: what the assistant, MCP, and the UI can do. Run: pytest"""

import pytest

from shared import db, focus, summary, tools
from tests.conftest import make_message

TODAY = summary.to_webex_utc(summary.datetime.now().astimezone())


@pytest.fixture
def no_background(monkeypatch):
    monkeypatch.setattr(summary, "summarize_session_in_background", lambda session_id: None)


def test_every_tool_has_a_schema_and_description():
    assert len(tools.TOOLS) >= 18
    for t in tools.TOOLS.values():
        assert t.description and t.schema["type"] == "object", t.name


def test_add_rule_and_list(tmp_db):
    out = tools.call("add_rule", {"category": "high", "match_type": "sender", "value": "bob@x.com"})
    assert "Added rule **#1**" in out["display"] and out["cards"][0]["type"] == "rule"
    assert "bob@x.com" in tools.call("list_rules")["display"]


def test_bad_arguments_become_friendly_errors(tmp_db):
    assert "Invalid arguments" in tools.call("add_rule", {"category": "urgent", "match_type": "sender"})["error"]
    assert "email" in tools.call("add_rule", {"category": "high", "match_type": "sender", "value": "Bob"})["error"]
    assert tools.call("no_such_tool")["error"]


def test_delete_needs_confirmation(tmp_db):
    tools.call("add_rule", {"category": "high", "match_type": "keyword", "value": "urgent"})
    ask = tools.call("delete_rule", {"rule_id": 1})
    assert ask["data"]["needs_confirmation"] and db.get_rule(1)
    tools.call("delete_rule", {"rule_id": 1, "confirm": True})
    assert db.get_rule(1) is None


def test_pause_rule(tmp_db):
    tools.call("add_rule", {"category": "high", "match_type": "keyword", "value": "urgent"})
    assert "paused" in tools.call("set_rule_enabled", {"rule_id": 1, "enabled": False})["display"]
    assert "There's no rule #9" in tools.call("set_rule_enabled", {"rule_id": 9, "enabled": False})["error"]


def test_focus_tools(tmp_db, no_background):
    assert "Focus is ON" in tools.call("set_focus_mode", {"on": True})["display"]
    assert focus.is_on()
    assert "Focus is ON" in tools.call("get_focus_status")["display"]
    assert "Focus is OFF" in tools.call("set_focus_mode", {"on": False})["display"]
    assert "already off" in tools.call("set_focus_mode", {"on": False})["display"]


def test_test_rule(tmp_db):
    tools.call("add_rule", {"category": "high", "match_type": "keyword", "value": "urgent"})
    out = tools.call("test_rule", {"text": "URGENT: server down"})
    assert out["data"]["category"] == "high" and "rule#1 keyword=urgent" in out["display"]
    assert tools.call("test_rule", {"text": "lunch?"})["data"]["category"] == "regular"


def test_search_contacts_spaces_and_feedback(tmp_db):
    db.insert_message(make_message("m1", email="carol@x.com", name="Carol Diaz", text="release moved", created=TODAY))
    db.insert_message(make_message("m2", email="bob@x.com", name="Bob Chen", room="Bob Chen", room_type="direct",
                                   created=TODAY))
    found = tools.call("search_messages", {"sender": "carol"})
    assert found["data"]["count"] == 1 and "release moved" in found["display"]
    assert tools.call("search_messages", {"contains": "release"})["data"]["count"] == 1
    assert tools.call("find_contacts", {"query": "bob"})["data"][0]["email"] == "bob@x.com"
    assert tools.call("find_spaces", {"query": "team"})["data"][0]["title"] == "Team Chat"
    marked = tools.call("mark_message", {"message_id": "m1", "label": "should_be_high"})
    assert "should have been **High priority**" in marked["display"]
    assert tools.call("get_triage_stats")["data"]["overall"]["reviewed"] == 1


def test_bad_dates_are_explained(tmp_db):
    assert "Dates must look like" in tools.call("search_messages", {"start": "last tuesday"})["error"]


def test_summarize_without_ai_uses_the_fallback(tmp_db):
    db.insert_message(make_message("m1", text="the deck is ready", created=TODAY))
    out = tools.call("summarize", {"scope": "held"})
    assert "the deck is ready" in out["display"] and "AI wasn't available" in out["display"]
    assert tools.call("list_summaries")["data"][0]["kind"] == "on_demand"


def test_summarize_empty_period(tmp_db):
    assert "Nothing to summarize" in tools.call("summarize")["display"]


def test_email_summary_writes_the_outbox(tmp_db):
    db.insert_message(make_message("m1", text="hello <b>there</b>", created=TODAY))
    sid = tools.call("summarize", {"scope": "all"})["data"]["id"]
    out = tools.call("email_summary", {"summary_id": sid})
    assert out["data"]["outbox_path"].endswith(".eml")
    assert db.get_summary(sid)["delivered_at"]
    html_files = list(summary.config.OUTBOX_DIR.glob("*.html"))
    assert html_files and "<b>there</b>" not in html_files[0].read_text()  # quoted HTML is escaped


def test_focus_profile(tmp_db):
    assert "Urgent" in tools.call("get_focus_profile")["data"]["profile"]
    tools.call("set_focus_profile", {"text": "Only outages are urgent for me."})
    assert tools.call("get_focus_profile")["data"]["profile"] == "Only outages are urgent for me."


def test_preview_rule_lists_messages_that_would_change(tmp_db):
    db.insert_message(make_message("m1", email="bob@x.com", category="regular", created=TODAY))
    db.insert_message(make_message("m2", email="carol@x.com", category="regular", created=TODAY))
    preview = tools.preview_rule("high", "sender", "bob@x.com")
    assert [m["id"] for m in preview["changed"]] == ["m1"] and preview["checked"] == 2
