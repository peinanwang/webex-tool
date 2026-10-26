# Phase 5 — One tool registry (shared by MCP and the agent)

**Status: built 2026-10-26** (automated tests pass). Hands-on checks: [VERIFY.md](../VERIFY.md).

Move the tools out of `mcp_server/server.py` into `shared/tools.py`, update them for v2, and add the new ones from [ai-tools.md](../ai-tools.md). After this phase, everything the assistant will be able to do already works from Claude Code. That is our test bench before we build our own agent.

## Learn first
- **What a tool is to an LLM**: a name, a description, and a JSON Schema for the arguments. The model never runs code. It replies "please call `add_rule` with these arguments", we run the function, and we send back the result.
- **Why one registry**: the in-app agent (Phase 6), the MCP server, and the UI API (Phase 8) all call the *same* Python functions. A fix in one place fixes all three, and Claude Code testing proves the agent's tools work.
- **Schema from type hints**: the `@tool` decorator reads the function's signature and docstring (with pydantic) to build the JSON Schema. Each tool is written once.

## Action items

### Registry (`shared/tools.py`)
- [ ] `@tool` decorator: registers `name → function`, plus the description (docstring) and the JSON Schema (from type hints)
- [ ] `TOOLS` list and `call(name, args) -> dict` (validates args and catches errors, returning `{"error": "…"}` so the model can explain or retry)
- [ ] Every tool returns `{"data": …, "display": render("chat/<tool>.md", …)}`

### Tools (see [ai-tools.md](../ai-tools.md))
- [ ] Focus: `get_focus_status`, `set_focus_mode`
- [ ] Rules: `list_rules`, `add_rule`, `set_rule_enabled`, `delete_rule`, `test_rule`, `find_contacts`, `find_spaces`
- [ ] Messages: `search_messages` (adds `contains`), `get_triage_stats`, `mark_message`
- [ ] Summary tools are stubs returning "coming in Phase 7" (keeps the catalog complete)
- [ ] Templates under `templates/chat/`: `focus_status.md`, `focus_on.md`, `focus_off.md`, `rules_list.md`, `rule_added.md`, `rule_removed.md`, `rule_toggled.md`, `rule_test.md`, `messages_list.md`, `triage_stats.md`, `feedback_saved.md`, `error.md`, plus sample data in `samples.yaml`

### MCP adapter (`mcp_server/server.py`)
- [ ] Replace the hand-written tools with a loop that registers every entry in `shared/tools.TOOLS` with the MCP server
- [ ] Keep the MCP `instructions` text, updated for `high` / `regular`
- [ ] Remove `get_digest_input` / `save_digest` / the file-based digests (summaries move to the DB in Phase 7)

### Tests
- [ ] `tests/test_tools.py`: runs each tool against a temporary DB (point `DB_PATH` at a tmp file) and checks `data`, plus that `display` renders

## Checkpoint
- [ ] `pytest` passes
- [ ] `/mcp` in Claude Code shows `webex-focus` with the new tool list
- [ ] Claude Code: "turn focus mode off" → `python -m shared.focus status` says off
- [ ] Claude Code: "notify me when Bob writes" → it calls `find_contacts`, then `add_rule(high, sender, bob@…)`
- [ ] Claude Code: "C's last message was actually important" → `feedback = should_be_high` on that row
- [ ] Claude Code: "how accurate was triage today?" → counts and accuracy
