---
subject: ethos:agent-projections
role: reference
state: canonical
relations:
  canonical_for: assistant and protocol surfaces
---

# Agent Projections

ETHOS is agentic-native, but assistant files, MCP resources, ACP adapters,
hosted runners, and provider-specific prompts are projections. They expose
repository truth; they do not become truth.

`ethos assistants doctor --json` reports the projection contract.
`ethos assistants mcp-manifest --json` emits resources, prompts, and tools that
agent hosts can load without copying ETHOS semantics into host-local state.

Projection rules:

- Keep the kernel free of assistant imports and host runtime dependencies.
- Keep MCP and ACP as protocol adapters over command JSON and docs.
- Keep host-local credentials, caches, and session logs out of repository truth.
- Retire a projection by removing the adapter while preserving kernel schemas,
  evidence, docs, and command contracts.
