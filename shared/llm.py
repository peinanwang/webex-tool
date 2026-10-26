"""The only module that talks to the LLM (OpenAI API, or later the company's OpenAI-compatible gateway).

Two calls:
- chat(): one step of the assistant's tool-calling loop (see shared/agent.py).
- extract(): get structured JSON back (summaries, AI triage). It uses a *forced tool call*: we
  define one function, e.g. `submit_summary(headline, highlights, ...)`, and require the model to
  call it. The arguments it fills in are our JSON. This works on older models and gateways that
  don't support newer JSON-schema response formats.

We use Chat Completions + `tools` (the most widely supported API shape), no parallel tool calls,
and no temperature/max_tokens (some newer models reject them). To switch to the company gateway,
set OPENAI_BASE_URL / OPENAI_API_KEY / LLM_MODEL in .env.

    python -m shared.llm "say hi"      # smoke test: key, model, proxy, certificates
    python -m shared.llm --models      # list models your key can use
"""

import json
import sys
import time

from shared import config
from shared.log import log


class LLMUnavailable(Exception):
    """No key, network error, timeout, auth failure, or quota: callers fall back to templates."""


_client = None
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def is_configured() -> bool:
    return bool(config.OPENAI_API_KEY)


def _get_client():
    global _client
    if not is_configured():
        raise LLMUnavailable("no OPENAI_API_KEY in .env")
    if _client is None:
        from openai import OpenAI  # imported lazily so the rest of the app runs without the package
        _client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL or DEFAULT_BASE_URL,
            organization=config.OPENAI_ORG_ID or None,
            project=config.OPENAI_PROJECT_ID or None,
            timeout=config.LLM_TIMEOUT,
            max_retries=1,
        )
    return _client


def _create(timeout: float | None = None, **kwargs):
    from openai import OpenAIError
    started = time.monotonic()
    try:
        resp = _get_client().chat.completions.create(timeout=timeout or config.LLM_TIMEOUT, **kwargs)
    except OpenAIError as exc:
        raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
    usage = getattr(resp, "usage", None)
    log(f"[llm] {kwargs.get('model')} {int((time.monotonic() - started) * 1000)}ms "
        f"tokens={getattr(usage, 'total_tokens', '?')}")
    return resp


def _parse_args(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {"_invalid_json": raw}


def chat(system: str, messages: list[dict], tools: list[dict] | None = None, model: str | None = None) -> dict:
    """One model step.

    Returns {"text": str | None, "tool_calls": [{"id", "name", "args"}], "message": <assistant message
    to append to the history before the tool results>}.
    """
    kwargs = {"model": model or config.LLM_MODEL, "messages": [{"role": "system", "content": system}, *messages]}
    if tools:
        kwargs["tools"] = tools
        kwargs["parallel_tool_calls"] = False  # one tool at a time: simpler loop, better on weak models
    msg = _create(**kwargs).choices[0].message
    calls = [{"id": c.id, "name": c.function.name, "args": _parse_args(c.function.arguments)}
             for c in (msg.tool_calls or [])]
    history_entry = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        history_entry["tool_calls"] = [
            {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in msg.tool_calls]
    return {"text": msg.content, "tool_calls": calls, "message": history_entry}


def extract(system: str, user: str, name: str, description: str, schema: dict,
            model: str | None = None, timeout: float | None = None) -> dict:
    """Structured output through a forced tool call. Returns the function arguments as a dict."""
    tool = {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}
    resp = _create(
        model=model or config.LLM_MODEL, timeout=timeout,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        tools=[tool], tool_choice={"type": "function", "function": {"name": name}},
    )
    calls = resp.choices[0].message.tool_calls or []
    if not calls:
        raise LLMUnavailable("the model didn't return structured output")
    args = _parse_args(calls[0].function.arguments)
    if "_invalid_json" in args:
        raise LLMUnavailable("the model returned malformed JSON")
    return args


if __name__ == "__main__":
    if "--models" in sys.argv:
        for m in sorted(_get_client().models.list(), key=lambda m: m.id):
            print(m.id)
        sys.exit(0)
    prompt = " ".join(sys.argv[1:]) or "Say hi in five words."
    print(f"Model: {config.LLM_MODEL}  Base URL: {config.OPENAI_BASE_URL or 'https://api.openai.com/v1'}")
    try:
        print(chat("You are a helpful assistant.", [{"role": "user", "content": prompt}])["text"])
    except LLMUnavailable as exc:
        raise SystemExit(f"LLM unavailable: {exc}")
