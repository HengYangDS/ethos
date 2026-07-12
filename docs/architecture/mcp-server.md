---
subject: ethos:mcp-server
role: explanation
state: canonical
relations:
  canonical_for: MCP adapter
---

# MCP Server

`ethos assistants mcp-server --serve` is a newline-delimited JSON-RPC stdio
server. It exposes only the fixed read-only `status`, `plan`, `explain`, and
context tools plus declared resources and prompts. It does not expose prove,
publish, land, or any generic command execution path; repository mutation and
proof remain on the admission-bound command plane.

The MCP surface is an adapter over repository truth.

`ethos assistants mcp-manifest --json` emits resources, prompts, and tools.
`ethos assistants mcp-server --json` describes the stdio server adapter contract.

The server descriptor does not create a second truth store. It exposes docs,
schemas, and command JSON to agent hosts.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
