# Phase 8 — Web UI, part 1: shell, Triage, Rules

The first two "review" tabs, plus the always-visible focus switch. Design and wireframes are in [ui.md](../ui.md).

## Learn first
- **SPA + JSON API**: the UI is a React app running in the browser. It only fetches JSON from FastAPI (`/api/...`) and draws it. FastAPI never builds HTML for these pages.
- **Dev vs. built**: while developing, `npm run dev` (Vite) serves the UI on port 5173 with instant reload and forwards `/api` calls to FastAPI on 8000. For the demo, `npm run build` writes static files to `ui/dist/`, and FastAPI serves them at `/`, so only one process runs.
- **API routes call tools**: each endpoint is a thin wrapper over a `shared/tools.py` function, so the UI and the assistant always agree.
- **localhost only**: the UI shows private messages and has no login. uvicorn listens on `127.0.0.1` by default. Never start it with `--host 0.0.0.0`.

## Action items

### Backend (`listener/api.py`, mounted in `listener/main.py`)
- [ ] `GET /api/status`, `POST /api/focus {on}`
- [ ] `GET /api/messages` (filters: period, category, sender, space, needs_review, q), `POST /api/messages/{id}/feedback {label}`, `GET /api/triage/stats`
- [ ] `GET/POST /api/rules`, `PATCH /api/rules/{id} {enabled}`, `DELETE /api/rules/{id}`, `POST /api/rules/test`
- [ ] `POST /api/rules/preview {category, match_type, value}`: re-evaluates today's messages with and without the new rule and returns the ones that would change
- [ ] `GET /api/contacts?q=`, `GET /api/spaces?q=` (autocomplete)
- [ ] Serve `ui/dist` at `/` when it exists
- [ ] `tests/test_api.py` with FastAPI's `TestClient`

### Frontend (`ui/`)
- [ ] Vite + React + TypeScript + Tailwind scaffold. `ui/README.md` with `npm install` / `npm run dev` / `npm run build`
- [ ] Shell: left sidebar (Assistant, Triage, Rules, Summaries, Templates; unbuilt tabs show "coming soon") and a top bar (focus switch, session timer and counts, last-poll indicator)
- [ ] **Triage tab**: period picker, category and "needs review" filters, search, rows with reason chips, feedback buttons, a stats line (reviewed and accuracy), and a side panel with "Create rule from this"
- [ ] **Rules tab**: plain-English rule list, on/off toggle, delete with confirmation, a new-rule form with autocomplete and impact preview, and a "try it" tester
- [ ] Wording on screen (button labels, empty states) lives in one file, `ui/src/copy.ts`, so it can be edited like the templates
- [ ] Refresh data every 5s for now (live push comes in Phase 9)

## Checkpoint
- [ ] `uvicorn listener.main:app --port 8000` + `npm run build` → `http://localhost:8000` opens the UI
- [ ] Toggle focus in the UI → `/status` in the Webex space agrees, and vice versa
- [ ] Triage shows today's messages with the correct category and reason
- [ ] Mark a regular message "↑ High" → `feedback` is saved, and the accuracy figure changes
- [ ] "Create rule from this" → form pre-filled → the preview says "would change N messages" → Save → the next message from that sender is `high`
- [ ] `pytest` passes, including the API tests
