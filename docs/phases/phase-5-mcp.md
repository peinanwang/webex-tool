# Phase 5 — MCP server: rules & message queries

Let A manage rules and ask about messages in plain language from Claude Code or VS Code Copilot.

## Learn first
- **MCP (Model Context Protocol)**: a standard way to give an AI assistant "tools" it can call. Our server lists tools like `add_rule`. The assistant decides when to call them and shows you the results.
- **stdio transport**: the IDE starts our MCP server as a child process and talks to it over stdin/stdout. No port and no URL. It only needs to read and write the same SQLite DB as the listener.
- **FastMCP**: the official Python SDK helper. A decorated Python function becomes a tool, and its docstring and type hints tell the model how to use it.

## Action items
- [ ] `mcp_server/server.py` (FastMCP, stdio):
  - [ ] `list_rules()`
  - [ ] `add_rule(action, match_type, value)`: validate inputs, return the new rule
  - [ ] `delete_rule(rule_id)` / `set_rule_enabled(rule_id, enabled)`
  - [ ] `get_messages(status=None, sender=None, space=None, start=None, end=None, limit=50)` (`status` can be `notify`, `digest`, `ignore`, or `self`)
  - [ ] `test_rule(text, sender_email, space)`: dry-run `evaluate()` to explain what would happen
- [ ] Clear docstrings on every tool (the model reads them)
- [ ] Register with Claude Code: `.mcp.json` in the repo root (command: `.venv/bin/python -m mcp_server.server`)
- [ ] (Optional) VS Code Copilot: `.vscode/mcp.json` with the same command
- [ ] Note: the listener reads rules from the DB on every message, so MCP changes take effect right away without a restart

## Checkpoint
- [ ] `/mcp` in Claude Code shows the server connected with its tools
- [ ] "Show my rules" lists the seeded rules
- [ ] "Add a notify rule for keyword 'outage'" → C sends "outage" → it gets relayed
- [ ] "What did C send today?" answers from the DB
