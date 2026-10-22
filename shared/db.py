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
