"""SQLite access shared by the listener and the MCP server.

Both processes open the same file. WAL mode lets the MCP server read while the listener writes.
Each function opens its own short-lived connection, which keeps things simple and thread-safe
(FastAPI may run our code on different threads).

Run `python -m shared.db` to create the database and list its tables.
"""

import sqlite3

from shared.config import DB_PATH, DIGESTS_DIR

SCHEMA = """
-- Small key/value store: OAuth tokens, A's personId, bot's personId, webhook id, polling cursors.
CREATE TABLE IF NOT EXISTS kv (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Every message the listener sees. `status` + `reason` explain what happened to it.
-- Times are Webex ISO-8601 UTC strings (e.g. 2026-10-21T14:03:00.000Z), so string
-- comparison works for time-range queries.
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,          -- Webex message id (also our dedupe key)
    room_id      TEXT NOT NULL,
    room_title   TEXT,
    room_type    TEXT,                      -- 'direct' (1:1) or 'group'
    person_id    TEXT,
    person_email TEXT,
    text         TEXT,
    created      TEXT NOT NULL,             -- when it was sent (from Webex)
    mentioned_me INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL CHECK (status IN ('notify', 'digest', 'ignore', 'self')),
    reason       TEXT NOT NULL,             -- which rule fired, e.g. 'rule#3 sender=b@...' or 'default'
    relayed_at   TEXT,                      -- when the Priority bot pinged A (notify only)
    logged_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created);

-- A's rules. `value` is empty for match_type 'mention'.
CREATE TABLE IF NOT EXISTS rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL CHECK (action IN ('notify', 'digest', 'ignore')),
    match_type TEXT NOT NULL CHECK (match_type IN ('sender', 'space', 'keyword', 'mention')),
    value      TEXT NOT NULL DEFAULT '',
    enabled    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # timeout: if the other process is mid-write, wait up to 10s instead of failing right away.
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["text"]
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


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


# --- messages ---

MESSAGE_COLUMNS = (
    "id", "room_id", "room_title", "room_type", "person_id", "person_email",
    "text", "created", "mentioned_me", "status", "reason",
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
            tuple(row[c] for c in MESSAGE_COLUMNS),
        )
    return cur.rowcount == 1


def mark_relayed(message_id: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE messages SET relayed_at = CURRENT_TIMESTAMP WHERE id = ?", (message_id,))


def query_messages(statuses: list[str] | None = None, sender: str | None = None, space: str | None = None,
                   start_utc: str | None = None, end_utc: str | None = None,
                   limit: int = 50, newest_first: bool = True) -> list[dict]:
    """Flexible message search for the MCP tools. sender/space match partially, ignoring case."""
    where, params = [], []
    if statuses:
        where.append(f"status IN ({', '.join('?' for _ in statuses)})")
        params += statuses
    if sender:
        where.append("person_email LIKE ?")
        params.append(f"%{sender}%")
    if space:
        where.append("room_title LIKE ?")
        params.append(f"%{space}%")
    if start_utc:
        where.append("created >= ?")
        params.append(start_utc)
    if end_utc:
        where.append("created < ?")
        params.append(end_utc)
    sql = "SELECT * FROM messages"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY created {'DESC' if newest_first else 'ASC'} LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def count_by_status(start_utc: str, end_utc: str) -> dict[str, int]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM messages WHERE created >= ? AND created < ? GROUP BY status",
            (start_utc, end_utc),
        )
        counts = {r["status"]: r["n"] for r in rows}
    return {s: counts.get(s, 0) for s in ("notify", "digest", "ignore", "self")}


def oldest_message_time() -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT MIN(created) AS t FROM messages").fetchone()
    return row["t"]


# --- rules ---

ACTIONS = ("notify", "digest", "ignore")
MATCH_TYPES = ("sender", "space", "keyword", "mention")


def list_rules(enabled_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM rules" + (" WHERE enabled = 1" if enabled_only else "") + " ORDER BY id"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql)]


def add_rule(action: str, match_type: str, value: str = "") -> dict:
    """Validate and store a rule. Raises ValueError with a readable message on bad input."""
    action, match_type, value = action.strip().lower(), match_type.strip().lower(), value.strip()
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}, got {action!r}")
    if match_type not in MATCH_TYPES:
        raise ValueError(f"match_type must be one of {MATCH_TYPES}, got {match_type!r}")
    if match_type == "mention":
        value = ""
    elif not value:
        raise ValueError(f"a {match_type} rule needs a value")
    with connect() as conn:
        cur = conn.execute("INSERT INTO rules (action, match_type, value) VALUES (?, ?, ?)",
                           (action, match_type, value))
        row = conn.execute("SELECT * FROM rules WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def delete_rule(rule_id: int) -> bool:
    with connect() as conn:
        return conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,)).rowcount == 1


def set_rule_enabled(rule_id: int, enabled: bool) -> bool:
    with connect() as conn:
        return conn.execute("UPDATE rules SET enabled = ? WHERE id = ?", (int(enabled), rule_id)).rowcount == 1


def delete_all_rules() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM rules")


if __name__ == "__main__":
    init_db()
    with connect() as conn:
        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    print(f"Database ready: {DB_PATH}")
    print(f"Tables: {', '.join(tables)}")
    print(f"Journal mode: {mode}")
