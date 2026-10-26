"""Shared pytest fixtures. pytest loads this file automatically."""

import pytest

from shared import config, db


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch, tmp_path):
    """Every test: no OpenAI calls, no desktop pop-ups, emails into a temp outbox."""
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "DESKTOP_NOTIFIER", "off")
    monkeypatch.setattr(config, "OUTBOX_DIR", tmp_path / "outbox")


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point shared.db at a fresh database in a temp folder, so tests never touch data/focus.db."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(db, "DIGESTS_DIR", tmp_path / "digests")
    db.init_db()
    return tmp_path / "test.db"


def make_message(id="m1", email="carol@x.com", name="Carol", room="Team Chat", room_type="group",
                 text="hello", category="regular", decided_by="default", reason="default",
                 created="2026-10-26T10:00:00.000Z", mentioned=0, focus_on=1) -> dict:
    """A stored-message row for tests."""
    return {"id": id, "room_id": f"room-{room}", "room_title": room, "room_type": room_type, "person_id": f"p-{email}",
            "person_email": email, "person_name": name, "text": text, "created": created, "mentioned_me": mentioned,
            "category": category, "reason": reason, "decided_by": decided_by, "focus_on": focus_on}
