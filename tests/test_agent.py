"""The assistant loop, with a fake LLM (no API calls). Run: pytest"""

import pytest

from shared import agent, config, db, llm, summary


@pytest.fixture
def fake_llm(tmp_db, monkeypatch):
    """Script the model's steps: each item is either text or (tool_name, args)."""
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(summary, "summarize_session_in_background", lambda session_id: None)
    script, seen = [], []

    def chat(system, messages, tools=None, model=None):
        seen.append(messages[:])
        step = script.pop(0)
        if isinstance(step, Exception):
            raise step
        if isinstance(step, str):
            return {"text": step, "tool_calls": [], "message": {"role": "assistant", "content": step}}
        name, args = step
        call = {"id": f"call-{len(seen)}", "name": name, "args": args}
        return {"text": None, "tool_calls": [call],
                "message": {"role": "assistant", "content": "", "tool_calls": [
                    {"id": call["id"], "type": "function", "function": {"name": name, "arguments": "{}"}}]}}

    monkeypatch.setattr(llm, "chat", chat)
    return script, seen


def test_tool_loop_adds_a_rule(fake_llm):
    script, seen = fake_llm
    script += [("add_rule", {"category": "high", "match_type": "keyword", "value": "outage"}), "✅ Done: outage is high."]
    db.add_chat("user", "notify me about outages", "webex")
    reply, cards = agent.reply("notify me about outages")
    assert reply == "✅ Done: outage is high."
    assert db.list_rules()[0]["value"] == "outage"
    assert cards[0]["type"] == "rule"
    assert seen[1][-1]["role"] == "tool"  # the tool result went back to the model


def test_step_cap(fake_llm, monkeypatch):
    script, _ = fake_llm
    monkeypatch.setattr(config, "AGENT_MAX_STEPS", 2)
    script += [("list_rules", {}), ("list_rules", {})]
    assert "couldn't finish" in agent.reply("loop forever")[0]


def test_llm_down_suggests_slash_commands(fake_llm):
    script, _ = fake_llm
    script.append(llm.LLMUnavailable("timeout"))
    assert "/focus on" in agent.reply("hello")[0]


def test_no_key_still_answers(tmp_db):
    assert "can't reach the AI" in agent.reply("show my rules")[0]


def test_slash_commands_need_no_llm(tmp_db, monkeypatch):
    monkeypatch.setattr(summary, "summarize_session_in_background", lambda session_id: None)
    assert "Focus is ON" in agent.reply("/focus on")[0]
    assert "Focus is ON" in agent.reply("/status")[0]
    assert "rules yet" in agent.reply("/rules")[0]
    assert "Focus is OFF" in agent.reply("/focus off")[0]
    assert "Nothing to summarize" in agent.reply("/summary focus")[0]
    assert "Quick commands" in agent.reply("/help")[0]
    assert "/dance" in agent.reply("/dance")[0]


def test_history_comes_from_chat(fake_llm):
    script, seen = fake_llm
    db.add_chat("user", "hi", "webex")
    db.add_chat("assistant", "hello!", "system")
    db.add_chat("notice", "🔔 alert", "system")  # alerts are not sent to the model
    db.add_chat("user", "what can you do?", "webex")
    script.append("Lots.")
    agent.reply("what can you do?")
    assert [m["content"] for m in seen[0]] == ["hi", "hello!", "what can you do?"]


# --- the expanded quick commands (no AI involved) ---

@pytest.fixture
def quiet(tmp_db, monkeypatch):
    monkeypatch.setattr(summary, "summarize_session_in_background", lambda session_id: None)


def test_mode_command(quiet):
    assert "Focus is OFF" in agent.reply("/mode")[0]
    assert "Focus is ON" in agent.reply("/mode on")[0]
    assert "Focus is ON" in agent.reply("/MODE")[0]          # command names ignore case
    assert "Focus is OFF" in agent.reply("/mode off")[0]
    assert "/help" in agent.reply("/mode sideways")[0]


def test_watch_unwatch_and_topic(quiet):
    assert "not watching any" in agent.reply("/watch")[0]
    assert 'Now watching the keyword "**outage**"' in agent.reply("/watch outage")[0]
    assert "Already watching" in agent.reply("/watch Outage")[0]
    assert "the topic **the Q3 launch**" in agent.reply("/topic the Q3 launch")[0]
    listing = agent.reply("/watch")[0]
    assert '"**outage**"' in listing and "the Q3 launch" in listing
    assert db.list_rules()[0]["category"] == "high"
    assert "Stopped watching" in agent.reply("/unwatch outage")[0]
    assert "not watching" in agent.reply("/unwatch outage")[0]


def test_rule_command(quiet):
    agent.reply("/watch urgent")
    assert "paused" in agent.reply("/rule off 1")[0]
    assert "back on" in agent.reply("/rule on #1")[0]
    assert "Deleted rule" in agent.reply("/rule delete 1")[0]  # explicit command: no confirmation step
    assert db.list_rules() == []
    assert "/help" in agent.reply("/rule zap 1")[0]


def test_profile_command_saves_text_verbatim(quiet):
    shown = agent.reply("/profile")[0]
    assert "What I pay attention to" in shown and "Learned from** 0 corrections" in shown
    out = agent.reply("/profile Only PROD outages are urgent; Questions can wait.")[0]
    assert "✅ Updated" in out and "Only PROD outages are urgent; Questions can wait." in out
    agent.reply("/watch outage")
    assert '"outage"' in agent.reply("/profile")[0]


def test_profile_explain_with_and_without_ai(quiet, monkeypatch):
    assert "can't reach the AI" in agent.reply("/profile explain")[0]
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "extract", lambda *a, **k: {"urgent": ["Production outages"],
                                                          "can_wait": ["Lunch chat"], "learned": []})
    out = agent.reply("/profile explain")[0]
    assert "I'll interrupt you for" in out and "- Production outages" in out and "Learned" not in out
