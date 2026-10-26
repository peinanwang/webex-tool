"""The UI's JSON API, through FastAPI's test client (no Webex, no lifespan). Run: pytest"""

import pytest
from fastapi.testclient import TestClient

from listener import api
from listener.main import app
from shared import db, summary
from tests.conftest import make_message


@pytest.fixture
def client(tmp_db, monkeypatch):
    monkeypatch.setattr(summary, "summarize_session_in_background", lambda session_id: None)
    replies = []
    monkeypatch.setattr(api.assistant, "start_reply", lambda text: replies.append(text))
    c = TestClient(app)  # used without `with`, so the lifespan (Webex login, polling) doesn't run
    c.replies = replies
    return c


def test_status_and_focus(client):
    assert client.get("/api/status").json()["focus"]["on"] is False
    assert client.post("/api/focus", json={"on": True}).json()["on"] is True
    assert client.get("/api/status").json()["focus"]["on"] is True


def test_rules_crud_and_preview(client):
    rule = client.post("/api/rules", json={"category": "high", "match_type": "keyword", "value": "outage"}).json()
    assert client.get("/api/rules").json()[0]["id"] == rule["id"]
    assert client.patch(f"/api/rules/{rule['id']}", json={"enabled": False}).json()["enabled"] is False
    assert client.post("/api/rules/test", json={"text": "outage!"}).json()["category"] == "regular"  # paused
    assert client.delete(f"/api/rules/{rule['id']}").status_code == 200
    bad = client.post("/api/rules", json={"category": "high", "match_type": "sender", "value": "Bob"})
    assert bad.status_code == 400 and "email" in bad.json()["detail"]
    assert client.post("/api/rules/preview", json={"category": "high", "match_type": "keyword",
                                                   "value": "x"}).json()["supported"]


def test_messages_and_feedback(client):
    created = summary.to_webex_utc(summary.datetime.now().astimezone())
    db.insert_message(make_message("m1", created=created))
    assert [m["id"] for m in client.get("/api/messages").json()] == ["m1"]
    assert client.post("/api/messages/m1/feedback", json={"label": "should_be_high"}).json()["feedback"] == "should_be_high"
    assert client.get("/api/triage/stats").json()["overall"]["reviewed"] == 1
    assert client.get("/api/contacts?q=carol").json()[0]["email"] == "carol@x.com"


def test_chat_post_stores_and_starts_a_reply(client):
    turn = client.post("/api/chat", json={"text": "show my rules"}).json()
    assert turn["role"] == "user" and turn["source"] == "ui"
    assert client.replies == ["show my rules"]
    assert client.get("/api/chat").json()[0]["text"] == "show my rules"


def test_summaries(client):
    s = client.post("/api/summaries", json={"scope": "held"}).json()
    assert client.get("/api/summaries").json()[0]["id"] == s["id"]
    emailed = client.post(f"/api/summaries/{s['id']}/email").json()
    name = emailed["outbox_path"].rsplit("/", 1)[-1].replace(".eml", ".html")
    page = client.get(f"/api/outbox/{name}")
    assert page.status_code == 200 and page.headers["content-security-policy"] == "sandbox"
    assert client.get("/api/outbox/..%2F..%2F.env").status_code == 404


def test_templates_api(client):
    names = [t["name"] for t in client.get("/api/templates").json()]
    assert "notify/assistant_post.md" in names
    info = client.get("/api/templates/notify/desktop_title.txt").json()
    assert info["placeholders"][0]["name"] == "sender"
    ok = client.post("/api/template-preview/notify/desktop_title.txt", json={"text": "Hi {{ sender }}"}).json()
    assert ok == {"ok": True, "output": "Hi Bob Chen"}
    bad = client.put("/api/templates/notify/desktop_title.txt", json={"text": "{{ sendr }}"})
    assert bad.status_code == 400 and "Did you mean" in bad.json()["detail"]
