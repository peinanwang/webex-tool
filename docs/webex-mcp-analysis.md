# Webex MCP: findings and decision

_Researched 2026-10-21. Webex's MCP offerings are new (June 2026) and some docs say "under development", so re-check before relying on details._

## Decision

**We build our own MCP server.** Webex's MCP offerings don't cover what this project does: real-time filtering, A's rules, and summaries of held messages. The Webex Messaging MCP is a possible add-on later, not a replacement.

## What Webex offers

Webex has two separate MCP offerings that work in opposite directions.

### 1. Webex-hosted MCP servers (Webex provides tools → your AI uses them)

Webex runs MCP servers that outside AI clients (Claude, ChatGPT, custom agents) can connect to:

| Server | Covers |
|---|---|
| Messaging | Spaces, direct messages, team chat history |
| Meetings | Transcripts, recordings, participants, summaries |
| Contact Center | Queues, call transcripts, agent status |
| Devices | Workspace sensors, room booking, environment controls |

**Messaging MCP server** (the relevant one):
- URL: `https://mcp.webexapis.com/mcp/webex-messaging` (hosted by Webex, remote)
- 24 tools: messages (create, edit, delete, get, search), spaces (5), memberships (4), webhooks (4), files (4), threads (2)
- Auth: OAuth token with `spark:mcp` plus messaging scopes; calls the Webex API as the signed-in user
- Requires an org admin to enable it in Control Hub
- Free personal accounts: not documented either way

### 2. "Onboard MCP" (you provide tools → Webex's AI uses them)

This is the "Onboard MCP" card on developer.webex.com. It registers your own MCP server as an "Agentic App" so Webex's AI agents can call it (examples: Salesforce, Jira, Confluence).
- Needs a **public HTTPS endpoint** (our stdio server can't be registered as it is)
- Needs admin approval for org use; optional App Hub publishing

## Why not use Webex's MCP for this project

| What the project needs | Webex Messaging MCP | Our design |
|---|---|---|
| React to every new message in real time | ❌ Request/response only; nothing happens unless the AI calls a tool | Listener (webhook or polling) |
| Ping A for important messages | ❌ | Listener + Priority bot |
| Store and manage A's rules | ❌ No concept of rules | Our MCP server (`add_rule`, `list_rules`, …) |
| Explain why a message was held or relayed | ❌ | `status` + `reason` on every stored message |
| Summarize what was held | ⚠️ The AI could read recent messages, but can't tell which were held | `get_digest_input(scope="held")` |
| Summarize any period across all spaces | ⚠️ Possible but slow: many API calls through the AI for each summary | One local DB query |
| Work on free personal accounts | ❓ Needs admin enablement; free-account support unknown | ✅ Uses a standard integration + bot |
| Work on the company network | ❓ Depends on the org enabling it | ✅ Polling mode needs outbound HTTPS only |

In short:
- **Wrong layer.** The core of the project is an always-on filter. MCP tools run only when an AI calls them, so no MCP server (Webex's or ours) can do real-time filtering. That's the listener's job.
- **Missing our data.** Rules, held/relayed status, and reasons exist only in our database. Webex's server can't know about them.
- **Access risk.** It needs admin enablement and may not work on free accounts, so a hackathon demo shouldn't depend on it.
- **"Onboard MCP" is the reverse direction.** It's for Webex's AI to call your tools. Our AI host is Claude Code / Copilot.

## Why build our own MCP server

- **It exposes our data.** Rules, message statuses and reasons, and digests live in our SQLite DB. A small FastMCP server is the simplest way to let Claude Code / Copilot read and change them in plain language.
- **It's small.** It's one Python file with about 10 tools, runs locally over stdio, and needs no public URL, hosting, or admin approval.
- **Summaries are fast and complete.** Every message the listener saw is already stored with its status, so a summary is one query.
- **The demo is under our control.** It works the same on personal accounts and the company network.

## Possible later use (stretch, after Phase 7)

- **Add Webex Messaging MCP next to ours in Claude Code.** For example: "summarize what I missed, then reply to B that I'll join at 3". Our server supplies the summary, and Webex's sends the reply.
- **Meetings MCP.** For example: "what did I miss in today's standup?" fits the focus idea.
- **Onboard our server as an Agentic App.** This would let A manage rules from Webex's own AI. It would need an HTTP transport, public hosting, and admin approval.

## Sources

- [Webex Messaging MCP Server: developer docs](https://developer.webex.com/mcp/docs/messaging-mcp-server)
- [Onboard Your MCP Server: developer docs](https://developer.webex.com/mcp/docs/onboard-your-mcp-server)
- [What's New for Agentic Apps: Webex Help Center](https://help.webex.com/en-us/article/nfp4yq0/What's-New-for-Agentic-Apps)
- [Webex Agentic MCP Servers: developer docs](https://developer.webex.com/create/docs/webex-agentic-mcp-servers)
- [CiscoDevNet/webex-mcp-official: Cisco Code Exchange](https://developer.cisco.com/codeexchange/github/repo/CiscoDevNet/webex-mcp-official/)
- [plugin-webex README (community; notes the official MCP has no real-time inbound messaging)](https://pkg.go.dev/github.com/mythingies/plugin-webex@v0.9.3)
