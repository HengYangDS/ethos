---
subject: docs:index
role: index
state: canonical
relations:
  canonical_for: docs navigation
---

# ETHOS Documentation

Status: canonical.

Purpose: provide stable navigation to current product, governance, architecture,
reference, and planning truth.

See also: [Documentation Root](README.md) and
[Command Plane](reference/command-plane.md).

Start with [Quickstart](start/quickstart.md), then read the
[Command Plane](reference/command-plane.md),
[Product Design Contract](governance/product-design-contract.md), and
[Terminal Governance Product Design](plans/terminal-governance-product-design.md).

## Discovery By Audience

| Audience | Start here | Then run | Boundary |
| --- | --- | --- | --- |
| Human operator | [Quickstart](start/quickstart.md) | `ethos status --json` | Reader view first; mutation requires Work Lane admission. |
| Coding agent | [AGENTS.md](../AGENTS.md) and a matching [rule](../rules/README.md) | `ethos status --json` | Repository truth outranks host memory and generated projections. |
| Maintainer | [Command Plane](reference/command-plane.md) | `ethos prove --full --json` | Executed proof supports a bounded Attestation verdict. |
| Adopter | [Adoption Profiles](architecture/adoption-profiles.md) | `ethos adopt --root <repo> --json` | One binding selects repository facts and proof depth. |

## Maps

- [Documentation Root](README.md)
- [Quickstart](start/quickstart.md)
- [Command Plane](reference/command-plane.md)
- [Product Design Contract](governance/product-design-contract.md)
- [Terminal Governance Product Design](plans/terminal-governance-product-design.md)
- [Tooling Adoption Roadmap](plans/tooling-adoption-roadmap.md)
- [Governance Documentation](governance/README.md)
- [OpenSpec Governance](governance/openspec-governance.md)
- [Repo-local Skills](governance/playbooks-and-skills.md)
- [Decision Records](decisions/README.md)
- [Architecture Documentation](architecture/)
- [Adoption Profiles](architecture/adoption-profiles.md)
- [Adopters](architecture/fleet-and-adopters.md)
- [Agent Projections](architecture/agent-projections.md)
- [MCP Adapter](architecture/mcp-server.md)
- [Local State](architecture/local-state.md)
- [Documentation Topology](architecture/docs-topology.md)
- [Generated Artifact Topology](architecture/generated-artifact-topology.md)
- [Docs Registry](governance/docs-registry.md)
- [Evidence Documentation](evidence/README.md)
- [Plans Documentation](plans/README.md)
- [History Documentation](history/README.md)
