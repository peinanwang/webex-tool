"""Database tests: v1 → v2 migration and message feedback. Run: pytest"""

import sqlite3

import pytest

from shared import db
from tests.conftest import make_message

# The v1 tables exactly as they were before the v2 plan (only the parts the migration reads).
V1_SCHEMA = """
CREATE TABLE kv (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE messages (
    id TEXT PRIMARY KEY, room_id TEXT NOT NULL, room_title TEXT, room_type TEXT, person_id TEXT,
    person_email TEXT, text TEXT, created TEXT NOT NULL, mentioned_me INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('notify', 'digest', 'ignore', 'self')),
    reason TEXT NOT NULL, relayed_at TEXT, logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX idx_messages_created ON messages (created);
CREATE TABLE rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL CHECK (action IN ('notify', 'digest', 'ignore')),
    match_type TEXT NOT NULL, value TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
INSERT INTO kv (key, value) VALUES ('refresh_token', 'keep-me');
INSERT INTO messages (id, room_id, created, status, reason, relayed_at) VALUES
    ('m1', 'r', '2026-10-22T10:00:00.000Z', 'notify', 'rule#1 sender=b@x.com', '2026-10-22 10:00:01'),
    ('m2', 'r', '2026-10-22T10:01:00.000Z', 'digest', 'default', NULL),
    ('m3', 'r', '2026-10-22T10:02:00.000Z', 'ignore', 'rule#2 space=Random', NULL),
    ('m4', 'r', '2026-10-22T10:03:00.000Z', 'self', 'self', NULL),
    ('m5', 'r', '2026-10-22T10:04:00.000Z', 'notify', 'default:mention', '2026-10-22 10:04:01');
INSERT INTO rules (id, action, match_type, value) VALUES
    (1, 'notify', 'sender', 'b@x.com'), (2, 'ignore', 'space', 'Random'), (3, 'digest', 'space', 'Team');
"""


@pytest.fixture
def v1_db(tmp_path, monkeypatch):
    path = tmp_path / "v1.db"
    conn = sqlite3.connect(path)
    conn.executescript(V1_SCHEMA)
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DIGESTS_DIR", tmp_path / "digests")
    return path


def test_fresh_db_needs_no_migration(tmp_db):
    assert db.init_db() == []


def test_v1_messages_and_rules_are_converted(v1_db):
    assert db.init_db() == ["messages", "rules"]

    rows = {r["id"]: r for r in db.query_messages(limit=10)}
    assert {k: (r["category"], r["decided_by"]) for k, r in rows.items()} == {
        "m1": ("high", "rule"), "m2": ("regular", "default"), "m3": ("regular", "rule"),
        "m4": ("self", "self"), "m5": ("high", "default"),
    }
    assert rows["m1"]["notified_at"] == "2026-10-22 10:00:01"

    assert [(r["id"], r["category"]) for r in db.list_rules()] == [(1, "high"), (2, "regular"), (3, "regular")]
    assert db.kv_get("refresh_token") == "keep-me"  # login survives


def test_migration_runs_once_and_keeps_index(v1_db):
    db.init_db()
    assert db.init_db() == []
    with db.connect() as conn:
        indexes = [r["name"] for r in conn.execute("PRAGMA index_list(messages)")]
    assert "idx_messages_created" in indexes


def test_new_rule_ids_continue_after_migrated_ones(v1_db):
    db.init_db()
    assert db.add_rule("high", "keyword", "outage")["id"] == 4


def test_add_rule_rejects_v1_actions(tmp_db):
    with pytest.raises(ValueError):
        db.add_rule("notify", "keyword", "x")


def test_feedback(tmp_db):
    db.insert_message(make_message("m1", category="regular"))
    assert db.set_feedback("m1", "should_be_high")["feedback"] == "should_be_high"
    assert db.set_feedback("missing", "correct") is None
    with pytest.raises(ValueError):
        db.set_feedback("m1", "important")


def test_feedback_matching_the_category_counts_as_correct(tmp_db):
    db.insert_message(make_message("m1", category="high", decided_by="rule"))
    assert db.set_feedback("m1", "should_be_high")["feedback"] == "correct"


def test_triage_stats_accuracy(tmp_db):
    db.insert_message(make_message("m1", category="high", decided_by="ai"))
    db.insert_message(make_message("m2", category="regular", decided_by="ai"))
    db.insert_message(make_message("m3", category="regular", decided_by="rule"))
    db.insert_message(make_message("m4", category="self", decided_by="self"))
    db.set_feedback("m1", "correct")
    db.set_feedback("m2", "should_be_high")
    stats = db.triage_stats("2026-10-26T00:00:00.000Z", "2026-10-27T00:00:00.000Z")
    assert (stats["total"], stats["high"], stats["regular"]) == (3, 1, 2)
    assert stats["ai"] == {"reviewed": 2, "correct": 1, "accuracy": 50}
    assert stats["needs_review"] == 0
    assert [r["label"] for r in db.labeled_examples()] == ["high", "high"]


def test_early_v2_rules_table_gets_topic(tmp_path, monkeypatch):
    path = tmp_path / "v2.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE rules (id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL CHECK (category IN ('high', 'regular')),
            match_type TEXT NOT NULL CHECK (match_type IN ('sender', 'space', 'keyword', 'mention')),
            value TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO rules (category, match_type, value) VALUES ('high', 'keyword', 'urgent');""")
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DIGESTS_DIR", tmp_path / "digests")
    assert db.init_db() == ["rules"]
    assert db.add_rule("high", "topic", "the Q3 launch")["id"] == 2


def test_sender_rule_needs_an_email(tmp_db):
    with pytest.raises(ValueError, match="email"):
        db.add_rule("high", "sender", "Bob")


def test_chat_and_summaries(tmp_db):
    db.add_chat("user", "hi", "webex")
    db.add_chat("assistant", "hello", "system", cards=[{"type": "rule", "id": 1}])
    db.add_chat("notice", "🔔 alert", "system")
    assert [t["role"] for t in db.list_chat(roles=("user", "assistant"))] == ["user", "assistant"]
    assert db.list_chat()[1]["cards"] == [{"type": "rule", "id": 1}]
    row = db.add_summary("on_demand", "a", "b", "held", "## hi", {"headline": "x"})
    assert db.get_summary(row["id"])["data"] == {"headline": "x"}


def test_reset_restarts_rule_numbering(tmp_db):
    db.add_rule("high", "keyword", "a")
    db.add_rule("high", "keyword", "b")
    db.delete_all_rules()
    assert db.add_rule("high", "keyword", "c")["id"] == 3  # plain delete keeps counting
    db.delete_all_rules(restart_numbering=True)
    assert db.add_rule("high", "keyword", "d")["id"] == 1
