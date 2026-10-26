# Webex Focus

Keep Webex quiet while you focus. Every new message is sorted into **High priority** (you get a desktop alert and a post in your private *Webex Assistant* space) or **Regular** (held for a summary). Chat with the assistant in Webex or in a local web page to manage rules, turn focus mode on and off, and get summaries.

- **How it works**: [docs/architecture.md](docs/architecture.md) · **What the AI can do**: [docs/ai-tools.md](docs/ai-tools.md) · **Web UI**: [docs/ui.md](docs/ui.md)
- **Try it end to end**: [docs/VERIFY.md](docs/VERIFY.md) · **Demo script**: [docs/DEMO.md](docs/DEMO.md) · **Roadmap**: [docs/PLAN.md](docs/PLAN.md)
- **Change the wording** (no code): [templates/README.md](templates/README.md)

## Setup (once)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in the Webex integration and OPENAI_API_KEY; macOS: DESKTOP_NOTIFIER=osascript
python -m scripts.login         # log in as yourself
# In Webex: create a space named exactly "Webex Assistant" with only you in it (ASSISTANT_SPACE_TITLE)
(cd ui && npm install && npm run build)
python -m scripts.reset_demo   # clean start: no rules (you create them by chatting)
```

## Run

You start with no rules. Set them by chatting in the Webex Assistant space, e.g. "notify me when Bob writes", "anything in Random can wait", "always notify me when I'm mentioned".


```bash
python -m listener              # → http://localhost:8000
```

Working on the web page? `./dev.sh` (real backend) or `./dev.sh sandbox` (fake data, no Webex) starts the backend **and** the UI dev server at http://localhost:5173 with instant reload; Ctrl+C stops both.

That one process polls Webex, triages messages, sends alerts, answers chat in the Webex Assistant space, runs the 23:59 summary, and serves the web page. It only listens on localhost (no login).

## Handy commands

| Command | What it does |
|---|---|
| `python -m shared.llm "say hi"` | Check the OpenAI key, model, and network |
| `python -m shared.desktop_notify "Test" "Hello"` | Check desktop notifications |
| `python -m shared.focus on\|off\|status` | Focus mode from the terminal |
| `python -m scripts.run_eod` | Make the end-of-day summary now (email → `data/outbox/`) |
| `python -m scripts.eval_triage` | AI triage accuracy against your corrections |
| `python -m scripts.eval_assistant` | Which tools the AI picks for typical requests |
| `python -m scripts.ui_sandbox` | Try the web page with fake data (no Webex; real data untouched) → http://localhost:8765 |
| `python -m scripts.ui_sandbox say carol "lunch?" --space Team` | Make a fake message arrive in the running sandbox |
| `pytest` | Automated tests (no Webex or OpenAI needed) |

## Company network

- **Polling** (`LISTENER_MODE=polling`) is the default. No ngrok, outbound HTTPS only.
- Set `HTTPS_PROXY` / `SSL_CERT_FILE` in `.env` if needed.
- The company LLM gateway: set `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `LLM_MODEL`.
- Real email: add a backend in `shared/emailer.py` (see its docstring).
