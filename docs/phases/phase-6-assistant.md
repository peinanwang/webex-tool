# Phase 6 — AI assistant in the Webex space

A chats with our own agent in the **Focus Assistant** space. The agent uses the Phase 5 tools through the **OpenAI API**. (The hackathon had a chat prototype with no tools. Its code isn't available, so this is a fresh build.)

## Learn first
- **Tool-calling loop**: send the model (system prompt + recent chat + tool list). If it asks for a tool, run it and send the result back, then repeat until it answers in text. We cap the loop at `AGENT_MAX_STEPS` (5) so a confused model can't spin forever.
- **Chat Completions + `tools`**: the OpenAI API call we use (`client.chat.completions.create(model, messages, tools)`). OpenAI has newer APIs, but this is the one company gateways and older models support most reliably, so the code moves to the company repo unchanged.
- **One swap point**: `shared/llm.py` is the only file that imports `openai`. Later the company repo changes `OPENAI_BASE_URL` / `OPENAI_API_KEY` (or this one file) to use its gateway.
- **Conversation memory**: the model remembers nothing between calls. We store each turn in `chat_messages` and send the last 20 turns each time.
- **Why slash commands**: `/focus off` should work instantly, cost nothing, and work when the LLM is down. Those commands skip the model.

## Action items

### Config (`.env.example`, `shared/config.py`)
- [ ] `OPENAI_API_KEY` (OpenAI authenticates with an API key, not a client id + secret), optional `OPENAI_ORG_ID` / `OPENAI_PROJECT_ID`
- [ ] `OPENAI_BASE_URL` (empty = `https://api.openai.com/v1`; the company gateway URL goes here later)
- [ ] `LLM_MODEL` (any chat model the key can use), `LLM_TIMEOUT=30`, `AGENT_MAX_STEPS=5`
- [ ] `requirements.txt`: `openai` (it uses httpx, so `HTTPS_PROXY` / `SSL_CERT_FILE` work the same as for Webex)

### LLM client (`shared/llm.py`)
- [ ] `chat(system, messages, tools) -> {"text": str | None, "tool_calls": [{"id", "name", "args"}]}`, a plain shape so `agent.py` never touches OpenAI types
- [ ] `extract(system, user, schema_name, json_schema) -> dict`: structured output through a **forced tool call** (`tool_choice` = that one function). It works on older models and gateways that lack JSON-schema response formats. Used by summaries (Phase 7) and AI triage (Phase 10)
- [ ] Turn off parallel tool calls (`parallel_tool_calls=False`), which makes the loop simpler and suits weaker models
- [ ] Timeout and one retry. Errors raise `LLMUnavailable`
- [ ] Log each call (model, tokens, ms) at debug level, without message text
- [ ] `python -m shared.llm "say hi"` as a smoke test for the key, model, proxy, and certificates

### Agent (`shared/agent.py`)
- [ ] New table `chat_messages (id, role, text, source, webex_message_id, cards_json, created_at)`
- [ ] `handle(text, source) -> reply`:
  - [ ] Slash commands → tool → template, with no LLM (`/help`, `/status`, `/focus on|off`, `/rules`, `/summary`)
  - [ ] Otherwise: system prompt from `templates/prompts/assistant.md` (values: A's name, today's date and time, focus status) + last 20 turns + `tools.TOOLS` → loop
  - [ ] Final text → `templates/chat/answer.md`. On `LLMUnavailable` → `templates/chat/llm_unavailable.md` (suggests slash commands)
  - [ ] Saves both turns. Keeps tool results' `data` as `cards_json` for the UI (Phase 9)
- [ ] Write `templates/prompts/assistant.md`: persona and tone, "reply with `display` as-is when it answers the request", "confirm before `delete_rule`", "never claim you did something without calling a tool", "if a name is ambiguous, ask", and 3–4 short example exchanges (examples help weaker models most)
- [ ] Keep tool descriptions short and concrete (one sentence + argument meanings + one example), since older models choose tools worse when descriptions are long
- [ ] Templates: `chat/help.md`, `chat/answer.md`, `chat/llm_unavailable.md`, `chat/not_understood.md`

### Wire into the listener (`listener/assistant.py`)
- [ ] Pipeline: a message from A in the assistant space that is not in `app_posts` → `assistant.on_user_message(msg)`
- [ ] Run the agent in a worker thread, so a 5-second LLM call doesn't pause polling
- [ ] Post the reply with `user_send` (recorded in `app_posts`)
- [ ] (Optional) Post "…" right away, then edit it into the answer (`PUT /v1/messages/{id}`), so A sees it's working

### Tests
- [ ] `tests/test_agent.py` with a fake LLM that returns scripted tool calls: checks the loop, the step cap, slash commands, and the LLM-down path. No real API calls
- [ ] `scripts/eval_assistant.py`: about 15 sample requests ("notify me when Bob writes", "pause the urgent rule", …) run against the real model with a temporary DB, printing which tool calls it made. Run it with `LLM_MODEL` set to your normal model **and** to a smaller/older one to mimic the company gateway

## Checkpoint
- [ ] `python -m shared.llm "say hi"` works
- [ ] In the Focus Assistant space: "what are my rules?" → the `rules_list` template text
- [ ] "Notify me when Bob writes" → `find_contacts` → rule added, confirmed with `rule_added` text
- [ ] "What did C say today?" → a correct answer from the DB
- [ ] "Delete rule 3" → it asks first, and deletes only after "yes"
- [ ] "Turn focus off" → focus off (`/status` confirms)
- [ ] Remove the API key → `/focus on` still works, and a normal question gets the `llm_unavailable` text
- [ ] The agent's replies are never processed as new user messages (no loop)
- [ ] `eval_assistant.py` passes most cases on a smaller model too (note which ones fail, for the company gateway)
