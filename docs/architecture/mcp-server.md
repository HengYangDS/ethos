---
subject: ethos:mcp-server
role: reference
state: canonical
relations:
  canonical_for: MCP adapter
---

# MCP Server

The MCP surface is an adapter over repository truth.

`ethos assistants mcp-manifest --json` emits resources, prompts, and tools.
`ethos assistants mcp-server --json` describes the stdio server adapter contract.

The server descriptor does not create a second truth store. It exposes docs,
schemas, and command JSON to agent hosts.
