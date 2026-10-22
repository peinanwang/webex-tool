# Phase 3 — Listener: receive & log messages (webhook + polling modes)

An always-running FastAPI app that picks up every new message in any space A is in. In this phase, every message is just logged. Rules come in Phase 4.

It supports two ways of finding new messages, chosen by `LISTENER_MODE` in `.env`:

| | `webhook` | `polling` |
|---|---|---|
| How | Webex POSTs to us when a message is created | We ask Webex every `POLL_INTERVAL` seconds |
| Speed | Instant | Up to ~10–15s delay |
| Needs | ngrok (public URL) | Outbound HTTPS only |
| Use for | Home / personal setup | Company network (ngrok likely blocked) |

Both modes call the same `process_message(message_id)` function, so everything after "we found a new message" is identical.

## Learn first
- **Webhook**: instead of us asking Webex, Webex sends an HTTP POST to our URL when something happens. That URL must be publicly reachable, which is why we use ngrok to expose `localhost:8000`.
- **Polling**: we ask Webex "anything new?" on a timer. It's slower and makes more API calls, but it only needs outgoing requests, which company firewalls allow.
- **Payload has IDs only**: for privacy, the webhook body doesn't include message text. We call `GET /v1/messages/{id}` with A's token to get it.
- **Signature**: Webex signs each webhook request with HMAC-SHA1 of the body using our webhook secret (`X-Spark-Signature`). We check it so random people can't post fake messages to our URL.
- **FastAPI lifespan**: code that runs once when the app starts and stops. We use it to register the webhook (webhook mode) or start the background polling loop (polling mode).

## Action items

### Shared pipeline (both modes)
- [ ] `listener/pipeline.py` → `process_message(message_id)`:
  - [ ] Skip if the id is already in `messages` (dedupe; polling may see a message twice)
  - [ ] Fetch the full message with A's token
  - [ ] Skip if `personId == Priority bot` (avoid loops)
  - [ ] If `personId == A`: store with `status='self'`, `reason='self'` and stop (no rules, no relay; kept so summaries show both sides)
  - [ ] Fetch the room title/type (cache it in memory)
  - [ ] Detect if A is mentioned (`mentionedPeople` contains A's personId)
  - [ ] Insert into `messages` with `status='digest'`, `reason='default'`
  - [ ] Print one line per message (`[digest] C in Team Chat: "…"`) so it's easy to watch during the demo
- [ ] `listener/main.py` (FastAPI): `GET /health` returns `{"ok": true, "mode": "<mode>"}`
- [ ] Lifespan reads `LISTENER_MODE` and starts the matching mode below

### Webhook mode
- [ ] `POST /webhook`:
  - [ ] Verify `X-Spark-Signature`; return 401 if it's wrong
  - [ ] Read `data.id` and hand it to `process_message` (as a background task)
  - [ ] Return 200 quickly (Webex retries slow or failed webhooks)
- [ ] On startup: delete any existing webhooks named "webex-focus", then register a new one for `messages` / `created` pointing to `PUBLIC_URL/webhook` with `WEBHOOK_SECRET` (the free ngrok URL changes on every restart)

### Polling mode
- [ ] `listener/poller.py`: background loop started from lifespan, every `POLL_INTERVAL` seconds:
  - [ ] `GET /v1/rooms?sortBy=lastactivity&max=50`
  - [ ] For each room with `lastActivity` newer than its cursor: `GET /v1/messages?roomId=…&max=50`
  - [ ] Process messages newer than the cursor, oldest first, through `process_message`
  - [ ] Update `poll_cursor:<roomId>` in `kv`
  - [ ] First run: set cursors to "now" so old history isn't imported
  - [ ] Catch and log errors, then keep looping (one bad call shouldn't stop polling)
- [ ] On startup in polling mode: delete any "webex-focus" webhook so the two modes never run at the same time

### Run notes (README)
- [ ] Webhook mode: start `ngrok http 8000`, copy the URL into `PUBLIC_URL`, then `uvicorn listener.main:app --port 8000`
- [ ] Polling mode: set `LISTENER_MODE=polling`, then `uvicorn listener.main:app --port 8000` (no ngrok)
- [ ] Company network: set `HTTPS_PROXY` / `SSL_CERT_FILE` if needed

## Checkpoint

### Webhook mode
- [ ] `curl localhost:8000/health` shows `"mode": "webhook"`
- [ ] Listener startup shows "webhook registered → https://…/webhook"
- [ ] B sends "hi" in the A↔B space, and a row appears in `messages` with the full text
- [ ] `curl -X POST localhost:8000/webhook -d '{}'` gets 401 (signature check works)

### Polling mode
- [ ] `curl localhost:8000/health` shows `"mode": "polling"`, and ngrok is not running
- [ ] Startup doesn't import old messages
- [ ] B sends "hi", and a row appears within ~`POLL_INTERVAL` seconds
- [ ] Restart the listener: no duplicate rows

### Both
- [ ] A sends a message, and it's logged with `status='self'`
- [ ] A message from the Priority bot is not logged
