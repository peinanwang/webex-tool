"""The assistant: turns one message from A into a reply.

1. Slash commands (/help, /mode, /profile, /watch, /topic, /rules, /rule, /summary; see SLASH_COMMANDS) run a
   tool directly: instant, free, and they work even when the LLM is down.
2. Anything else goes to the LLM with the tool list. The tool-calling loop:
   ask the model → if it wants a tool, run it and send the result back → repeat until it answers in
   text (at most AGENT_MAX_STEPS tool rounds, so a confused model can't spin forever).
3. The final text is wrapped by templates/chat/answer.md.

The model remembers nothing between calls, so each turn sends the last AGENT_HISTORY_TURNS chat
turns from chat_messages. Callers store the user's turn and post the reply (listener/assistant.py,
listener/api.py); reply() itself only computes it.
"""

import json
from datetime import datetime

from shared import config, db, focus, llm, tools
from shared.log import log
from shared.templates import render
from shared.timeutil import parse_webex

MAX_TOOL_RESULT_CHARS = 6000


def _out(outcome: dict) -> tuple[str, list]:
    return outcome["display"], outcome.get("cards", [])


def _usage(command: str) -> tuple[str, list]:
    return render("chat/unknown_command.md", command=command), []


def _summary_of_last_focus_session() -> tuple[str, list]:
    session = db.last_focus_session()
    if not session:
        return render("chat/error.md", message="There hasn't been a focus session yet."), []
    end = session["ended_at"] or None
    return _out(tools.call("summarize", {"start": parse_webex(session["started_at"]).isoformat(timespec="minutes"),
                                         "end": parse_webex(end).isoformat(timespec="minutes") if end else "",
                                         "scope": "held"}))


def _slash_mode(arg: str):
    if arg.lower() in ("on", "off"):
        return _out(tools.call("set_focus_mode", {"on": arg.lower() == "on"}))
    return _out(tools.call("get_focus_status")) if not arg else _usage(f"/mode {arg}")


def _slash_rule(arg: str):
    """/rule on N · /rule off N · /rule delete N (explicit, so no extra confirmation)."""
    parts = arg.split()
    if len(parts) != 2 or parts[0].lower() not in ("on", "off", "delete") or not parts[1].lstrip("#").isdigit():
        return _usage(f"/rule {arg}".strip())
    action, rule_id = parts[0].lower(), int(parts[1].lstrip("#"))
    if action == "delete":
        return _out(tools.call("delete_rule", {"rule_id": rule_id, "confirm": True}))
    return _out(tools.call("set_rule_enabled", {"rule_id": rule_id, "enabled": action == "on"}))


def _slash_profile(arg: str):
    if not arg:
        return _out(tools.call("get_focus_profile"))
    if arg.lower() == "explain":
        return _out(tools.call("explain_focus_profile"))
    return _out(tools.call("set_focus_profile", {"text": arg}))  # saved exactly as typed


def _slash_summary(arg: str):
    if arg.lower() == "focus":
        return _summary_of_last_focus_session()
    return _out(tools.call("summarize", {"scope": "all" if arg.lower() == "all" else "held"}))


# Slash commands: instant, free, and they work when the AI is down. The text after the command is
# passed as typed (e.g. "/profile Only outages are urgent." is saved word for word).
SLASH_COMMANDS = {
    "/help": lambda arg: (render("chat/help.md", llm_ready=llm.is_configured()), []),
    "/mode": _slash_mode,
    "/status": _slash_mode,
    "/focus": lambda arg: _slash_mode(arg) if arg.lower() in ("on", "off") else _usage(f"/focus {arg}".strip()),
    "/rules": lambda arg: _out(tools.call("list_rules")),
    "/rule": _slash_rule,
    "/profile": _slash_profile,
    "/watch": lambda arg: _out(tools.call("watch", {"text": arg}) if arg else tools.call("list_watches")),
    "/unwatch": lambda arg: _out(tools.call("unwatch", {"text": arg})) if arg else _usage("/unwatch"),
    "/topic": lambda arg: _out(tools.call("watch", {"text": arg, "kind": "topic"}) if arg else tools.call("list_watches")),
    "/summary": _slash_summary,
}


def _slash(text: str) -> tuple[str, list]:
    command, _, arg = text.strip().partition(" ")
    handler = SLASH_COMMANDS.get(command.lower())
    return handler(arg.strip()) if handler else _usage(text.strip())


def _system_prompt() -> str:
    now = datetime.now().astimezone()
    status = focus.status()
    return render("prompts/assistant.md", user_name=db.kv_get("my_display_name") or "the user",
                  now=now.strftime("%A %Y-%m-%d %H:%M"), today=now.date().isoformat(),
                  timezone=now.strftime("%Z"), focus_on=status["on"])


def _history() -> list[dict]:
    """Recent user/assistant turns in OpenAI's message format (alerts and notices left out)."""
    turns = db.list_chat(limit=config.AGENT_HISTORY_TURNS, roles=("user", "assistant"))
    return [{"role": t["role"], "content": t["text"]} for t in turns]


def _tool_message(call_id: str, outcome: dict) -> dict:
    payload = {k: outcome.get(k) for k in ("display", "data", "error") if outcome.get(k) is not None}
    content = json.dumps(payload, default=str, ensure_ascii=False)
    if len(content) > MAX_TOOL_RESULT_CHARS:
        content = content[:MAX_TOOL_RESULT_CHARS] + "… (truncated)"
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def reply(text: str) -> tuple[str, list]:
    """Compute the assistant's reply to A's message. Returns (markdown, cards). Never raises.

    Expects A's turn to already be stored in chat_messages (it's the last turn of the history).
    """
    text = text.strip()
    if text.startswith("/"):
        return _slash(text)
    if not llm.is_configured():
        return render("chat/llm_unavailable.md", reason="no OpenAI API key is set up"), []

    messages = _history()
    if not messages or messages[-1] != {"role": "user", "content": text}:
        messages.append({"role": "user", "content": text})
    cards: list = []
    specs = tools.openai_specs()
    try:
        system = _system_prompt()
        for _ in range(config.AGENT_MAX_STEPS):
            step = llm.chat(system, messages, specs)
            if not step["tool_calls"]:
                answer = (step["text"] or "").strip()
                if not answer:
                    break
                return render("chat/answer.md", answer=answer), cards
            messages.append(step["message"])
            for call in step["tool_calls"]:
                log(f"[agent] tool {call['name']}({json.dumps(call['args'], ensure_ascii=False)[:200]})")
                outcome = tools.call(call["name"], call["args"])
                cards.extend(outcome.get("cards") or [])
                messages.append(_tool_message(call["id"], outcome))
        return render("chat/not_understood.md"), cards
    except llm.LLMUnavailable as exc:
        log(f"[agent] LLM unavailable: {exc}")
        return render("chat/llm_unavailable.md", reason=str(exc)), cards
    except Exception as exc:
        log(f"[error] agent failed: {exc!r}")
        return render("chat/error.md", message=f"Something went wrong: {exc}"), cards
