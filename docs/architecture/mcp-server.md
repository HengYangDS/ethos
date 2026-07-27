---
subject: ethos:mcp-adapter
role: explanation
state: canonical
relations:
  canonical_for: MCP adapter boundary
---

# MCP Adapter

Status: canonical.

Purpose: define MCP as a replaceable projection over repository truth.

See also: [Agent Projections](agent-projections.md) and
[Command Plane](../reference/command-plane.md).

MCP integrations are not public ETHOS lifecycle commands and do not own task,
change, evidence, or authorization state. They may expose declared resources or
guarded tools only through an admitted adapter contract.

No MCP implementation or smoke gate is currently admitted. A future adapter
must bring its own consumer, permissions, conformance tests, and uninstall proof;
the core lifecycle remains complete without it.
