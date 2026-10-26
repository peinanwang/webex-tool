"""Webex Focus MCP server: the same tools as the in-app assistant, for Claude Code / VS Code Copilot.

The IDE starts this file as a child process and talks to it over stdin/stdout (stdio transport).
Every tool comes from shared/tools.py, so the IDE, the Webex chat, and the UI all behave the same.
It reads and writes the same SQLite DB as the listener, so rule changes apply to the very next message.

Never print() here: stdout is the MCP channel, and stray output would corrupt it (shared code logs
to stderr via shared.log).

Registered in .mcp.json (Claude Code) and .vscode/mcp.json (Copilot).
"""

import functools
import sys
from pathlib import Path

# The IDE may launch us from any working directory, so make the project root importable
# (for `shared.*`) before importing it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from shared import db, tools  # noqa: E402

mcp = MCPServer(
    "webex-focus",
    instructions=(
        "Webex Focus keeps the user's Webex quiet. A listener stores every message with a category: "
        "high (important; the user is notified while focus mode is on), regular (held for the summary), "
        "self (sent by the user). Use these tools to manage focus mode and rules, look up messages, give "
        "triage feedback, and make summaries. Each result has `display` (ready-made text: show it as-is "
        "when it answers the question) and `data`. Dates and times are in the user's local time."
    ),
)

db.init_db()


def _safe(entry: tools.Tool):
    """Wrap a tool so bad input comes back as a readable result instead of an MCP error.

    functools.wraps keeps the original signature, which MCP reads to build the argument schema.
    """
    @functools.wraps(entry.fn)
    def run(**kwargs):
        return tools.call(entry.name, kwargs)
    return run


for _entry in tools.TOOLS.values():
    mcp.add_tool(_safe(_entry), name=_entry.name, description=_entry.description)


@mcp.prompt()
def daily_digest(start: str = "", end: str = "", scope: str = "held") -> str:
    """Summarize Webex messages for a period (default: what I missed today)."""
    return (f"Call the summarize tool with start={start!r}, end={end!r}, scope={scope!r}, "
            "then show me its `display` text as-is.")


if __name__ == "__main__":
    mcp.run()  # stdio transport
