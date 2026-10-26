"""Start the app:  python -m listener

Same as `uvicorn listener.main:app --port 8000`, with two choices made for you:
- host 127.0.0.1: the UI and API have no login, so they're only reachable from this computer.
- a short graceful-shutdown timeout: open browser tabs keep a live-updates connection open, which
  would otherwise make Ctrl+C wait.
"""

import uvicorn

from shared import config

if __name__ == "__main__":
    uvicorn.run("listener.main:app", host="127.0.0.1", port=config.PORT, timeout_graceful_shutdown=2)
