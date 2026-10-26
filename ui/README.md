# Webex Focus UI

React + Vite + TypeScript + Tailwind. It talks only to the Python app's JSON API (`/api/...`, see `listener/api.py`).

Easiest, from the repo root: `./dev.sh` (real backend) or `./dev.sh sandbox` (fake data). It starts the Python backend and this dev server together, with `/api` forwarded to the backend's port (`BACKEND_URL`).

```bash
npm install        # once
npm run build      # → ui/dist/, served by the Python app at http://localhost:8000
npm run dev        # while changing the UI: http://localhost:5173 with instant reload (Python app must be running)
```

- `src/copy.ts` holds the on-screen labels (edit wording there, like the templates).
- `src/tabs/` has one file per page: Assistant, Triage, Rules, Summaries, Templates.
- Live updates arrive over Server-Sent Events (`/api/events`), handled in `src/useEvents.ts`.
