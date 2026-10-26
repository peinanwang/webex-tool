#!/usr/bin/env bash
# Run Webex Focus for UI work: the Python backend + the UI dev server (instant reload),
# with the UI forwarding its /api calls to the backend's port.
#
#   ./dev.sh             real backend: python -m listener (needs your Webex login; port PORT from .env, default 8000)
#   ./dev.sh sandbox     fake-data backend: python -m scripts.ui_sandbox (no Webex, your data untouched; port 8765)
#
# It opens http://localhost:5173 (other port: UI_PORT=5174 ./dev.sh; don't open a browser: NO_OPEN=1 ./dev.sh).
# Ctrl+C stops both.
# In sandbox mode, make messages arrive from another terminal:
#   python -m scripts.ui_sandbox say carol "lunch anyone?" --space Team
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-real}"
PY=".venv/bin/python"
UI_PORT="${UI_PORT:-5173}"

usage() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; }

case "$MODE" in
  real)
    # Same port the listener uses: PORT from the environment, else from .env, else 8000.
    BACKEND_PORT="${PORT:-$(grep -E '^[[:space:]]*PORT[[:space:]]*=' .env 2>/dev/null | tail -1 | cut -d= -f2 | tr -d ' "' || true)}"
    BACKEND_PORT="${BACKEND_PORT:-8000}"
    BACKEND_CMD=("$PY" -m listener)
    ;;
  sandbox)
    BACKEND_PORT=8765
    BACKEND_CMD=("$PY" -m scripts.ui_sandbox)
    ;;
  -h|--help|help) usage; exit 0 ;;
  *) echo "Unknown mode '$MODE'."; echo; usage; exit 1 ;;
esac

# --- checks ---
[ -x "$PY" ] || { echo "No Python environment. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }
command -v npm >/dev/null || { echo "npm not found. Install Node.js (e.g. brew install node)."; exit 1; }
for port in "$BACKEND_PORT" "$UI_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop whatever is running there (another ./dev.sh or python -m listener?) and retry."
    exit 1
  fi
done
if [ ! -d ui/node_modules ]; then
  echo "Installing UI dependencies (first run only)..."
  (cd ui && npm install)
fi

# --- start both; stop both on Ctrl+C or if either one exits ---
BACKEND_PID=""; UI_PID=""
cleanup() {
  trap - INT TERM EXIT
  echo; echo "Stopping..."
  [ -n "$UI_PID" ] && kill "$UI_PID" 2>/dev/null || true
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Starting the backend ($MODE) on port $BACKEND_PORT..."
PORT="$BACKEND_PORT" "${BACKEND_CMD[@]}" &
BACKEND_PID=$!

for _ in $(seq 1 60); do
  curl -s -o /dev/null "http://127.0.0.1:$BACKEND_PORT/api/status" && break
  kill -0 "$BACKEND_PID" 2>/dev/null || { echo "The backend stopped during startup (see the messages above)."; exit 1; }
  sleep 1
done
curl -s -o /dev/null "http://127.0.0.1:$BACKEND_PORT/api/status" || { echo "The backend didn't answer on port $BACKEND_PORT within 60s."; exit 1; }

echo "Starting the UI dev server on port $UI_PORT (forwarding /api to port $BACKEND_PORT)..."
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT" UI_PORT="$UI_PORT" ./ui/node_modules/.bin/vite ui --clearScreen false &
UI_PID=$!

for _ in $(seq 1 30); do
  curl -s -o /dev/null "http://localhost:$UI_PORT/" && break
  sleep 1
done
echo
echo "  ➜  Webex Focus UI: http://localhost:$UI_PORT   (backend: http://127.0.0.1:$BACKEND_PORT, mode: $MODE)"
echo "     Edit files in ui/src and the page reloads. Ctrl+C stops both."
echo
[ -z "${NO_OPEN:-}" ] && command -v open >/dev/null && open "http://localhost:$UI_PORT" || true

# Keep running while both are alive (macOS ships bash 3.2, which has no `wait -n`).
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$UI_PID" 2>/dev/null; do sleep 1; done
echo "One of the two processes stopped."
