---
subject: ethos:agent-projections
role: reference
state: canonical
relations:
  canonical_for: assistant and protocol surfaces
---

# Agent Projections

ETHOS is agentic-native, but assistant files, MCP resources, ACP adapters,
hosted runners, provider-specific prompts, and provider-visible skill packages
are projections. They expose repository truth; they do not become truth.

`ethos assistants doctor --json` reports the projection contract.
`ethos assistants mcp-manifest --json` emits resources, prompts, and tools that
agent hosts can load without copying ETHOS semantics into host-local state.
MCP resources, prompts, and tools carry capability classifications so hosts can
distinguish read-only context, prompt templates, proof commands, and guarded
mutation affordances.

Repo-local Skills V2 packages follow the same boundary. `SKILL.md` is a
loadable workflow package, `package.toml` is package inventory and digest
metadata, and `.agents/skills/activation.toml` is the ETHOS activation registry
input. None of those surfaces can introduce repository truth outside source,
tests, schemas, canonical docs, promoted OpenSpec records, claims, evidence, and
command JSON.

Projection rules:

- Keep the kernel free of assistant imports and host runtime dependencies.
- Keep MCP and ACP as protocol adapters over command JSON and docs.
- Keep skill package manifests authority-thin: they declare package files,
  digest state, required sections, and capability classes, not product truth.
- Use `ethos quality projection-drift --json` to compare skill package,
  registry, and playbook-generator digests before treating projections as fresh.
- Keep host-local credentials, caches, and session logs out of repository truth.
- Retire a projection by removing the adapter while preserving kernel schemas,
  evidence, docs, and command contracts.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
