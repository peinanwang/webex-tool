"""SQLite access shared by the listener and the MCP server.

Both processes open the same file. WAL mode lets the MCP server read while the listener writes.
Each function opens its own short-lived connection, which keeps things simple and thread-safe
(FastAPI may run our code on different threads).

Run `python -m shared.db` to create the database (or upgrade an older one) and list its tables.
"""

import json
import sqlite3

from shared.config import DB_PATH, DIGESTS_DIR
from shared.timeutil import now_webex_utc

# Each table is its own string so a migration can create a fresh copy of one table.
KV_TABLE = """
-- Small key/value store: OAuth tokens, A's personId, webhook id, polling cursors,
-- focus mode state, focus profile, Webex Assistant space id.
CREATE TABLE IF NOT EXISTS kv (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

MESSAGES_TABLE = """
-- Every message the listener sees (except the Webex Assistant space, which is chat_messages).
-- `category` + `reason` explain what happened to it.
-- Times are Webex ISO-8601 UTC strings (e.g. 2026-10-21T14:03:00.000Z), so string
-- comparison works for time-range queries.
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,          -- Webex message id (also our dedupe key)
    room_id      TEXT NOT NULL,
    room_title   TEXT,
    room_type    TEXT,                      -- 'direct' (1:1) or 'group'
    person_id    TEXT,
    person_email TEXT,
    person_name  TEXT,
    text         TEXT,
    created      TEXT NOT NULL,             -- when it was sent (from Webex)
    mentioned_me INTEGER NOT NULL DEFAULT 0,
    category     TEXT NOT NULL CHECK (category IN ('high', 'regular', 'self')),
    reason       TEXT NOT NULL,             -- e.g. 'rule#3 sender=b@...', 'default:mention', 'ai: ...'
    decided_by   TEXT NOT NULL CHECK (decided_by IN ('rule', 'default', 'ai', 'self')),
    focus_on     INTEGER NOT NULL DEFAULT 0, -- was focus mode on when it arrived?
    notified_at  TEXT,                      -- when A was notified (high + focus on only)
    feedback     TEXT CHECK (feedback IN ('correct', 'should_be_high', 'should_be_regular')),
    feedback_at  TEXT,
    logged_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

RULES_TABLE = """
-- A's rules. `value` is empty for match_type 'mention'. 'topic' rules are judged by AI triage.
CREATE TABLE IF NOT EXISTS rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    category   TEXT NOT NULL CHECK (category IN ('high', 'regular')),
    match_type TEXT NOT NULL CHECK (match_type IN ('sender', 'space', 'keyword', 'mention', 'topic')),
    value      TEXT NOT NULL DEFAULT '',
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

OTHER_TABLES = """
-- One row per "focus on → focus off" stretch. ended_at is NULL while the session is running.
-- Times are Webex-style UTC strings, like messages.created, so they compare directly.
CREATE TABLE IF NOT EXISTS focus_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at   TEXT,
    summary_id INTEGER
);

-- Ids of messages we posted as A (integration). The pipeline skips them: without this, polling
-- would read our own replies in the Webex Assistant space as A's chat input (a loop).
CREATE TABLE IF NOT EXISTS app_posts (
    webex_message_id TEXT PRIMARY KEY,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- The conversation with the assistant: one thread, shown in the Webex Assistant space and the UI.
-- role: 'user' (A), 'assistant' (the AI's replies), 'notice' (automatic posts: alerts, summaries).
CREATE TABLE IF NOT EXISTS chat_messages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    role             TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'notice')),
    text             TEXT NOT NULL,
    source           TEXT NOT NULL CHECK (source IN ('webex', 'ui', 'system')),
    webex_message_id TEXT,
    cards_json       TEXT,                  -- structured tool results the UI renders as cards
    created_at       TEXT NOT NULL
);

-- Saved summaries. data_json = what the AI returned; markdown = after the template.
CREATE TABLE IF NOT EXISTS summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL CHECK (kind IN ('on_demand', 'focus_session', 'end_of_day')),
    period_start TEXT NOT NULL,
    period_end   TEXT NOT NULL,
    scope        TEXT NOT NULL CHECK (scope IN ('held', 'all')),
    data_json    TEXT,
    markdown     TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    delivered_at TEXT,                      -- when it was "emailed" (written to the outbox)
    delivered_to TEXT                       -- outbox file path for now
);

CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created);
"""

SCHEMA = KV_TABLE + MESSAGES_TABLE + RULES_TABLE + OTHER_TABLES

# --- migrations ---
# Each runs inside one transaction (BEGIN ... COMMIT), so a failure leaves the old tables untouched.
# Pattern: rename the old table, create the current version, copy rows (converting values), drop
# the old one. The index is recreated afterwards by SCHEMA. `kv` (login tokens) is never touched.

MIGRATE_MESSAGES_V1 = f"""
DROP INDEX IF EXISTS idx_messages_created;
ALTER TABLE messages RENAME TO messages_v1;
{MESSAGES_TABLE}
INSERT INTO messages (id, room_id, room_title, room_type, person_id, person_email, text, created,
                      mentioned_me, category, reason, decided_by, notified_at, logged_at)
SELECT id, room_id, room_title, room_type, person_id, person_email, text, created, mentioned_me,
       CASE status WHEN 'notify' THEN 'high' WHEN 'self' THEN 'self' ELSE 'regular' END,
       reason,
       CASE WHEN status = 'self' THEN 'self' WHEN reason LIKE 'default%' THEN 'default' ELSE 'rule' END,
       relayed_at, logged_at
FROM messages_v1;
DROP TABLE messages_v1;
"""


def _rebuild_rules(category_expr: str) -> str:
    # Keep the ids: stored message reasons like 'rule#3 ...' refer to them.
    return f"""
ALTER TABLE rules RENAME TO rules_old;
{RULES_TABLE}
INSERT INTO rules (id, category, match_type, value, enabled, created_at)
SELECT id, {category_expr}, match_type, value, enabled, created_at FROM rules_old;
DROP TABLE rules_old;
"""


# Columns added after a table first shipped: (table, column, definition).
ADDED_COLUMNS = [("messages", "person_name", "TEXT")]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # timeout: if the other process is mid-write, wait up to 10s instead of failing right away.
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["text"]
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _table_sql(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row["sql"] if row else ""


def _migrate(conn: sqlite3.Connection) -> list[str]:
    """Upgrade older tables in place. Returns what was converted."""
    steps = {}
    if "status" in _columns(conn, "messages"):
        steps["messages"] = MIGRATE_MESSAGES_V1
    rules_sql = _table_sql(conn, "rules")
    if "action" in _columns(conn, "rules"):
        steps["rules"] = _rebuild_rules("CASE action WHEN 'notify' THEN 'high' ELSE 'regular' END")
    elif rules_sql and "'topic'" not in rules_sql:
        steps["rules"] = _rebuild_rules("category")  # early v2 table: allow the new 'topic' match type
    if steps:
        conn.executescript("BEGIN;\n" + "\n".join(steps.values()) + "\nCOMMIT;")
    for table, column, definition in ADDED_COLUMNS:
        existing = _columns(conn, table)
        if existing and column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return list(steps)


def init_db() -> list[str]:
    """Create missing tables, upgrading older tables first. Returns the names of migrated tables.

    Never prints: the MCP server calls this, and its stdout is the MCP channel.
    """
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        migrated = _migrate(conn)
        conn.executescript(SCHEMA)
    return migrated


# --- kv helpers ---

def kv_get(key: str, default: str | None = None) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def kv_set(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO kv (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP",
            (key, value),
        )


def kv_delete_prefix(prefix: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM kv WHERE key LIKE ?", (prefix + "%",))


# --- messages ---

CATEGORIES = ("high", "regular")          # what triage (rules, defaults, AI) can decide
MESSAGE_CATEGORIES = CATEGORIES + ("self",)
FEEDBACK_LABELS = ("correct", "should_be_high", "should_be_regular")

MESSAGE_COLUMNS = (
    "id", "room_id", "room_title", "room_type", "person_id", "person_email", "person_name",
    "text", "created", "mentioned_me", "category", "reason", "decided_by", "focus_on",
)


def message_exists(message_id: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM messages WHERE id = ?", (message_id,)).fetchone() is not None


def insert_message(row: dict) -> bool:
    """Store a message. Returns False if it was already stored (duplicate delivery)."""
    placeholders = ", ".join("?" for _ in MESSAGE_COLUMNS)
    with connect() as conn:
        cur = conn.execute(
            f"INSERT OR IGNORE INTO messages ({', '.join(MESSAGE_COLUMNS)}) VALUES ({placeholders})",
            tuple(row.get(c) for c in MESSAGE_COLUMNS),
        )
    return cur.rowcount == 1


def get_message(message_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return dict(row) if row else None


def mark_notified(message_id: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE messages SET notified_at = CURRENT_TIMESTAMP WHERE id = ?", (message_id,))


def set_feedback(message_id: str, label: str) -> dict | None:
    """Record A's verdict on a message's category. Returns the updated row, or None if no such message.

    'should_be_high' on a message that is already high just means "correct", so it's stored that way;
    that keeps the accuracy numbers honest.
    """
    if label not in FEEDBACK_LABELS:
        raise ValueError(f"label must be one of {FEEDBACK_LABELS}, got {label!r}")
    row = get_message(message_id)
    if not row:
        return None
    if label == f"should_be_{row['category']}":
        label = "correct"
    with connect() as conn:
        conn.execute("UPDATE messages SET feedback = ?, feedback_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (label, message_id))
    return get_message(message_id)


def query_messages(categories: list[str] | None = None, sender: str | None = None, space: str | None = None,
                   start_utc: str | None = None, end_utc: str | None = None, contains: str | None = None,
                   needs_review: bool = False, limit: int = 50, newest_first: bool = True) -> list[dict]:
    """Flexible message search. sender/space/contains match partially, ignoring case.

    sender matches the email or the display name. needs_review = AI-decided and not reviewed yet.
    """
    where, params = [], []
    if categories:
        where.append(f"category IN ({', '.join('?' for _ in categories)})")
        params += categories
    if sender:
        where.append("(person_email LIKE ? OR person_name LIKE ?)")
        params += [f"%{sender}%", f"%{sender}%"]
    if space:
        where.append("room_title LIKE ?")
        params.append(f"%{space}%")
    if contains:
        where.append("text LIKE ?")
        params.append(f"%{contains}%")
    if start_utc:
        where.append("created >= ?")
        params.append(start_utc)
    if end_utc:
        where.append("created < ?")
        params.append(end_utc)
    if needs_review:
        where.append("decided_by = 'ai' AND feedback IS NULL")
    sql = "SELECT * FROM messages"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY created {'DESC' if newest_first else 'ASC'} LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def count_by_category(start_utc: str, end_utc: str) -> dict[str, int]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n FROM messages WHERE created >= ? AND created < ? GROUP BY category",
            (start_utc, end_utc),
        )
        counts = {r["category"]: r["n"] for r in rows}
    return {c: counts.get(c, 0) for c in MESSAGE_CATEGORIES}


def triage_stats(start_utc: str, end_utc: str) -> dict:
    """Counts plus accuracy from A's feedback (excluding A's own messages)."""
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT category, decided_by, feedback FROM messages "
            "WHERE created >= ? AND created < ? AND category != 'self'", (start_utc, end_utc))]

    def accuracy(subset: list[dict]) -> dict:
        reviewed = [r for r in subset if r["feedback"]]
        correct = sum(r["feedback"] == "correct" for r in reviewed)
        return {"reviewed": len(reviewed), "correct": correct,
                "accuracy": round(100 * correct / len(reviewed)) if reviewed else None}

    return {
        "total": len(rows),
        "high": sum(r["category"] == "high" for r in rows),
        "regular": sum(r["category"] == "regular" for r in rows),
        "needs_review": sum(r["decided_by"] == "ai" and not r["feedback"] for r in rows),
        "overall": accuracy(rows),
        "rules": accuracy([r for r in rows if r["decided_by"] == "rule"]),
        "defaults": accuracy([r for r in rows if r["decided_by"] == "default"]),
        "ai": accuracy([r for r in rows if r["decided_by"] == "ai"]),
    }


def labeled_examples(limit: int = 10) -> list[dict]:
    """Messages A has reviewed, newest first, with the right answer in `label` (for AI triage examples)."""
    with connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM messages WHERE feedback IS NOT NULL AND category != 'self' "
            "ORDER BY feedback_at DESC LIMIT ?", (limit,))]
    for r in rows:
        r["label"] = r["category"] if r["feedback"] == "correct" else r["feedback"].removeprefix("should_be_")
    return rows


def count_feedback() -> int:
    """How many messages A has reviewed (the AI learns from these)."""
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM messages WHERE feedback IS NOT NULL").fetchone()["n"]


def known_contacts(query: str, limit: int = 5) -> list[dict]:
    """People who have messaged A, matching a partial name or email."""
    like = f"%{query}%"
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT person_email AS email, MAX(person_name) AS name, COUNT(*) AS messages FROM messages "
            "WHERE category != 'self' AND person_email != '' AND (person_email LIKE ? OR person_name LIKE ?) "
            "GROUP BY person_email ORDER BY messages DESC LIMIT ?", (like, like, limit))]


def known_spaces(query: str = "", limit: int = 10) -> list[dict]:
    """Spaces we've seen messages in, matching a partial title."""
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT room_title AS title, MAX(room_type) AS type, COUNT(*) AS messages FROM messages "
            "WHERE room_title LIKE ? GROUP BY room_title ORDER BY messages DESC LIMIT ?",
            (f"%{query}%", limit))]


def oldest_message_time() -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT MIN(created) AS t FROM messages").fetchone()
    return row["t"]


# --- rules ---

MATCH_TYPES = ("sender", "space", "keyword", "mention", "topic")


def list_rules(enabled_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM rules" + (" WHERE enabled = 1" if enabled_only else "") + " ORDER BY id"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql)]


def get_rule(rule_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
    return dict(row) if row else None


def validate_rule(category: str, match_type: str, value: str = "") -> tuple[str, str, str]:
    """Normalize a rule's fields. Raises ValueError with a readable message on bad input."""
    category, match_type, value = category.strip().lower(), match_type.strip().lower(), value.strip()
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")
    if match_type not in MATCH_TYPES:
        raise ValueError(f"match_type must be one of {MATCH_TYPES}, got {match_type!r}")
    if match_type == "mention":
        value = ""
    elif not value:
        raise ValueError(f"a {match_type} rule needs a value")
    if match_type == "sender" and "@" not in value:
        raise ValueError(f"a sender rule needs an email address, got {value!r} (look it up with find_contacts)")
    return category, match_type, value


def add_rule(category: str, match_type: str, value: str = "") -> dict:
    """Validate and store a rule. Raises ValueError with a readable message on bad input."""
    category, match_type, value = validate_rule(category, match_type, value)
    with connect() as conn:
        cur = conn.execute("INSERT INTO rules (category, match_type, value) VALUES (?, ?, ?)",
                           (category, match_type, value))
        row = conn.execute("SELECT * FROM rules WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def delete_rule(rule_id: int) -> bool:
    with connect() as conn:
        return conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,)).rowcount == 1


def set_rule_enabled(rule_id: int, enabled: bool) -> bool:
    with connect() as conn:
        return conn.execute("UPDATE rules SET enabled = ? WHERE id = ?", (int(enabled), rule_id)).rowcount == 1


def delete_all_rules(restart_numbering: bool = False) -> None:
    """Delete every rule. restart_numbering=True makes the next rule #1 again; only do that when stored
    messages are cleared too (their reasons, like 'rule#3 ...', refer to rule numbers)."""
    with connect() as conn:
        conn.execute("DELETE FROM rules")
        if restart_numbering:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'rules'")


# --- focus sessions (state lives in kv; see shared/focus.py) ---

def start_focus_session(started_at: str) -> int:
    with connect() as conn:
        return conn.execute("INSERT INTO focus_sessions (started_at) VALUES (?)", (started_at,)).lastrowid


def end_focus_session(session_id: int, ended_at: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE focus_sessions SET ended_at = ? WHERE id = ?", (ended_at, session_id))


def get_focus_session(session_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def last_focus_session() -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM focus_sessions ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def set_session_summary(session_id: int, summary_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE focus_sessions SET summary_id = ? WHERE id = ?", (summary_id, session_id))


# --- our own posts ---

def add_app_post(webex_message_id: str) -> None:
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO app_posts (webex_message_id) VALUES (?)", (webex_message_id,))


def is_app_post(webex_message_id: str) -> bool:
    with connect() as conn:
        return conn.execute("SELECT 1 FROM app_posts WHERE webex_message_id = ?",
                            (webex_message_id,)).fetchone() is not None


# --- chat ---

def _chat_view(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["cards"] = json.loads(d.pop("cards_json") or "[]")
    return d


def add_chat(role: str, text: str, source: str, webex_message_id: str | None = None,
             cards: list | None = None) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO chat_messages (role, text, source, webex_message_id, cards_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (role, text, source, webex_message_id, json.dumps(cards or [], default=str), now_webex_utc()))
        return _chat_view(conn.execute("SELECT * FROM chat_messages WHERE id = ?", (cur.lastrowid,)).fetchone())


def set_chat_webex_id(chat_id: int, webex_message_id: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE chat_messages SET webex_message_id = ? WHERE id = ?", (webex_message_id, chat_id))


def list_chat(limit: int = 100, before_id: int | None = None, roles: tuple[str, ...] | None = None) -> list[dict]:
    """Chat turns, oldest first (the newest `limit` of them, or those before `before_id`)."""
    where, params = [], []
    if before_id:
        where.append("id < ?")
        params.append(before_id)
    if roles:
        where.append(f"role IN ({', '.join('?' for _ in roles)})")
        params += list(roles)
    sql = "SELECT * FROM chat_messages" + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = [_chat_view(r) for r in conn.execute(sql, params)]
    return list(reversed(rows))


# --- summaries ---

def _summary_view(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["data"] = json.loads(d.pop("data_json") or "null")
    return d


def add_summary(kind: str, period_start: str, period_end: str, scope: str, markdown: str,
                data: dict | None) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO summaries (kind, period_start, period_end, scope, data_json, markdown, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kind, period_start, period_end, scope, json.dumps(data) if data else None, markdown, now_webex_utc()))
        return _summary_view(conn.execute("SELECT * FROM summaries WHERE id = ?", (cur.lastrowid,)).fetchone())


def update_summary(summary_id: int, markdown: str, data: dict | None) -> None:
    with connect() as conn:
        conn.execute("UPDATE summaries SET markdown = ?, data_json = ?, created_at = ? WHERE id = ?",
                     (markdown, json.dumps(data) if data else None, now_webex_utc(), summary_id))


def get_summary(summary_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,)).fetchone()
    return _summary_view(row) if row else None


def list_summaries(kind: str | None = None, limit: int = 20) -> list[dict]:
    sql = "SELECT * FROM summaries" + (" WHERE kind = ?" if kind else "") + " ORDER BY id DESC LIMIT ?"
    params = ([kind] if kind else []) + [limit]
    with connect() as conn:
        return [_summary_view(r) for r in conn.execute(sql, params)]


def mark_summary_delivered(summary_id: int, delivered_to: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE summaries SET delivered_at = ?, delivered_to = ? WHERE id = ?",
                     (now_webex_utc(), delivered_to, summary_id))


# --- demo reset ---

def clear_activity() -> None:
    """Delete messages, chat, summaries, and focus sessions. Keeps rules, login, and cursors."""
    with connect() as conn:
        for table in ("messages", "chat_messages", "summaries", "focus_sessions", "app_posts"):
            conn.execute(f"DELETE FROM {table}")


if __name__ == "__main__":
    migrated = init_db()
    with connect() as conn:
        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    print(f"Database ready: {DB_PATH}")
    if migrated:
        print(f"Upgraded: {', '.join(migrated)} (v1 notify → high, digest/ignore → regular)")
    print(f"Tables: {', '.join(tables)}")
    print(f"Journal mode: {mode}")
