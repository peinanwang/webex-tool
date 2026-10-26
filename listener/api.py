"""JSON API for the web UI (ui/), plus Server-Sent Events for live updates.

Each endpoint is a thin wrapper over the same functions the assistant uses (shared/tools.py), so a
button in the UI and a sentence in chat always do exactly the same thing.

FastAPI notes:
- `def` endpoints (not `async def`) run in a thread pool, so slow work (an LLM call) doesn't block
  other requests.
- Request bodies are pydantic models: FastAPI validates the JSON and returns a 422 error if a field
  is missing or has the wrong type.
- This API has no login, so the listener only listens on 127.0.0.1 (see listener/__main__.py).
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from listener import assistant, poller
from shared import config, db, events, llm, summary, templates, tools, triage_ai
from shared.assistant_space import chat_view, mirror_user_text, room_id
from shared.tools import ToolError, message_view, rule_view
from shared.timeutil import period_bounds, to_webex_utc

router = APIRouter(prefix="/api")


def _run(name: str, **args) -> dict:
    """Call a tool; turn its error into an HTTP 400 with the friendly message."""
    outcome = tools.call(name, args)
    if outcome.get("error"):
        raise HTTPException(status_code=400, detail=outcome["error"])
    return outcome


# --- status & focus ---

@router.get("/status")
def get_status():
    return {
        "focus": tools.focus_view(),
        "user": {"name": db.kv_get("my_display_name"), "email": db.kv_get("my_email")},
        "listener": {"mode": config.LISTENER_MODE, "poll_interval": config.POLL_INTERVAL,
                     "last_ok_at": poller.last_ok_at, "last_error": poller.last_error},
        "assistant_space": bool(room_id()),
        "llm": {"configured": llm.is_configured(), "model": config.LLM_MODEL},
        "ai_triage": triage_ai.enabled(),
        "notify_channels": config.NOTIFY_CHANNELS,
    }


class FocusBody(BaseModel):
    on: bool


@router.post("/focus")
def set_focus(body: FocusBody):
    return _run("set_focus_mode", on=body.on)["data"]


# --- messages & triage ---

@router.get("/messages")
def get_messages(start: str = "", end: str = "", category: str = "", sender: str = "", space: str = "",
                 q: str = "", needs_review: bool = False, limit: int = 200):
    start_dt, end_dt = period_bounds(start or None, end or None)
    rows = db.query_messages(categories=[category] if category else None, sender=sender or None,
                             space=space or None, contains=q or None, start_utc=to_webex_utc(start_dt),
                             end_utc=to_webex_utc(end_dt), needs_review=needs_review, limit=min(limit, 1000))
    return [message_view(r) for r in rows]


@router.get("/messages/{message_id}")
def get_message(message_id: str):
    row = db.get_message(message_id)
    if not row:
        raise HTTPException(status_code=404, detail="No such message.")
    return message_view(row)


class FeedbackBody(BaseModel):
    label: str


@router.post("/messages/{message_id}/feedback")
def post_feedback(message_id: str, body: FeedbackBody):
    return _run("mark_message", message_id=message_id, label=body.label)["data"]


@router.get("/triage/stats")
def triage_stats(start: str = "", end: str = ""):
    return _run("get_triage_stats", start=start, end=end)["data"]


# --- rules ---

@router.get("/rules")
def get_rules():
    return [rule_view(r) for r in db.list_rules()]


class RuleBody(BaseModel):
    category: str
    match_type: str
    value: str = ""


@router.post("/rules")
def post_rule(body: RuleBody):
    return _run("add_rule", category=body.category, match_type=body.match_type, value=body.value)["data"]


class RuleEnabledBody(BaseModel):
    enabled: bool


@router.patch("/rules/{rule_id}")
def patch_rule(rule_id: int, body: RuleEnabledBody):
    return _run("set_rule_enabled", rule_id=rule_id, enabled=body.enabled)["data"]


@router.delete("/rules/{rule_id}")
def remove_rule(rule_id: int):
    return _run("delete_rule", rule_id=rule_id, confirm=True)["data"]  # the UI asks before calling


class RuleTestBody(BaseModel):
    text: str
    sender_email: str = ""
    space: str = ""
    mentioned: bool = False


@router.post("/rules/test")
def test_rule(body: RuleTestBody):
    return _run("test_rule", **body.model_dump())["data"]


@router.post("/rules/preview")
def preview_rule(body: RuleBody):
    try:
        return tools.preview_rule(body.category, body.match_type, body.value)
    except ToolError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/contacts")
def contacts(q: str = ""):
    return db.known_contacts(q, limit=10)


@router.get("/spaces")
def spaces(q: str = ""):
    return db.known_spaces(q)


class ProfileBody(BaseModel):
    text: str


@router.get("/focus-profile")
def get_profile():
    return {"profile": triage_ai.get_profile(), "ai_triage_on": triage_ai.enabled()}


@router.put("/focus-profile")
def put_profile(body: ProfileBody):
    return _run("set_focus_profile", text=body.text)["data"]


# --- chat ---

@router.get("/chat")
def get_chat(limit: int = 200, before: int | None = None):
    return [chat_view(r) for r in db.list_chat(limit=min(limit, 500), before_id=before)]


class ChatBody(BaseModel):
    text: str


@router.post("/chat")
def post_chat(body: ChatBody):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Type a message first.")
    row = mirror_user_text(text)    # stored + copied into the Webex space (marked as our own post)
    assistant.start_reply(text)     # the reply arrives over /api/events
    return chat_view(row)


# --- summaries ---

@router.get("/summaries")
def get_summaries(kind: str = "", limit: int = 50):
    return [summary.summary_view(r) for r in db.list_summaries(kind or None, min(limit, 200))]


@router.get("/summaries/{summary_id}")
def get_summary(summary_id: int):
    row = db.get_summary(summary_id)
    if not row:
        raise HTTPException(status_code=404, detail="No such summary.")
    return summary.summary_view(row)


class SummaryBody(BaseModel):
    start: str = ""
    end: str = ""
    scope: str = "held"


@router.post("/summaries")
def create_summary(body: SummaryBody):
    return _run("summarize", start=body.start, end=body.end, scope=body.scope)["data"]


@router.post("/summaries/{summary_id}/regenerate")
def regenerate_summary(summary_id: int):
    try:
        return summary.summary_view(summary.regenerate(summary_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/summaries/{summary_id}/email")
def email_summary(summary_id: int):
    return _run("email_summary", summary_id=summary_id)["data"]


@router.get("/outbox/{name}")
def outbox_file(name: str):
    """Serve an outbox email preview (.html) so the UI can open it in a new tab."""
    path = (config.OUTBOX_DIR / name).resolve()
    if path.parent != config.OUTBOX_DIR.resolve() or path.suffix != ".html" or not path.exists():
        raise HTTPException(status_code=404, detail="No such email in the outbox.")
    # sandbox: the preview can't run scripts even if a quoted message contained some.
    return FileResponse(path, media_type="text/html", headers={"Content-Security-Policy": "sandbox"})


# --- templates (for non-technical editors) ---

@router.get("/templates")
def list_templates():
    return templates.list_templates()


@router.get("/templates/{name:path}")
def get_template(name: str):
    try:
        return templates.get_template_info(name)
    except (templates.TemplateProblem, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


class TemplateBody(BaseModel):
    text: str


@router.post("/template-preview/{name:path}")
def preview_template(name: str, body: TemplateBody):
    try:
        return {"ok": True, "output": templates.preview(name, body.text)}
    except templates.TemplateProblem as exc:
        return {"ok": False, "error": str(exc)}


@router.put("/templates/{name:path}")
def save_template(name: str, body: TemplateBody):
    try:
        return {"ok": True, "output": templates.save(name, body.text)}
    except templates.TemplateProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/template-reset/{name:path}")
def reset_template(name: str):
    try:
        return {"ok": True, "text": templates.reset(name)}
    except templates.TemplateProblem as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# --- live updates ---

@router.get("/events")
async def event_stream(request: Request):
    """Server-Sent Events: one long response the server keeps writing events into.

    Each event is two lines, `event: <type>` and `data: <json>`, then a blank line. The browser's
    EventSource reads them and reconnects by itself if the connection drops.
    """
    queue = events.subscribe()

    async def stream():
        try:
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # comment line; stops proxies from closing an idle stream
                    continue
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], default=str)}\n\n"
        finally:
            events.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
