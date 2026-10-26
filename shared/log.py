"""One-line logging to stderr.

Shared code runs inside the MCP server too, where stdout is the MCP channel and a stray print()
would corrupt it. stderr is safe in both processes and still shows up in the listener's terminal.
"""

import sys


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)
