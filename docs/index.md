---
subject: docs:index
role: reference
state: canonical
relations:
  canonical_for: docs navigation
---

# ETHOS Documentation

Status: canonical.

Purpose: provide the stable navigation map for ETHOS product truth, governance,
architecture, reference, and evidence docs.

See also: [Quickstart](start/quickstart.md), [Command Plane](reference/command-plane.md),
and [Glossary](reference/glossary.md).

Start with [Start](start/quickstart.md), then read
[Kernel Model](concepts/kernel-model.md),
[Product Design Contract](governance/product-design-contract.md),
[Terminal Governance Product Design](architecture/terminal-governance-product-design.md),
[Package Ontology](architecture/package-ontology.md),
[Product Boundary Convergence](governance/product-boundary-convergence.md),
[Capability Parity Ledger](governance/capability-parity-ledger.md),
[Repository Profile Contract](governance/repository-profile-contract.md),
[Config Boundary Model](governance/config-boundary-model.md),
[Adopter Boundary And Retirement](governance/adopter-boundary-and-retirement.md),
[Distribution](architecture/distribution.md),
[Action Graph](architecture/action-graph.md), and
[Evolution](governance/evolution-campaign.md). Product gaps captured
from the design conversation are tracked in the
[Conversation Ledger](governance/conversation-ledger.md).
Executable migration parity is exposed by `ethos parity ledger` and governed by
the [Capability Parity Ledger](governance/capability-parity-ledger.md).

The documentation system uses Subject, Role, State, and Relation metadata so
humans and agents can navigate without treating historical or planned material as canonical truth without checking front matter state and evidence.

## Discovery By Audience

| Audience | Start here | Then run | Boundary |
| --- | --- | --- | --- |
| Human operator | [Quickstart](start/quickstart.md) | `ethos orient` | Reader view first; mutation only after an explicit Work Lane or authorized apply path. |
| Coding agent | [AGENTS.md](../AGENTS.md) and the matching [rule](../rules/README.md) | `ethos orient --json` | Repository truth outranks host memory, chat context, and generated projections. |
| Maintainer | [Command Plane](reference/command-plane.md) | `ethos report --json` and HEAD-bound `ethos prove` | Scorecards explain readiness; executed proof supports claims. |
| Adopter | [Adoption Profiles](architecture/adoption-profiles.md) | `ethos adopt --dry-run --json` | Profiles change gates and adapters, not the governed repository kind. |

In multi-agent work, visible foreign Work Lanes and unbound Work Lane refs are
read models over Git, lease, claim, and evidence facts. Use them to coordinate,
not to write, land, retire, or clean another lane or ref without owner handoff
or maintainer break-glass evidence.

## Maps

- Root docs: [Documentation Root](README.md)
- Start: [Quickstart](start/quickstart.md)
- Concepts: [Kernel Model](concepts/kernel-model.md)
- Command plane: [Command Plane](reference/command-plane.md)
- Glossary: [Glossary](reference/glossary.md)
- Product design contract: [Product Design Contract](governance/product-design-contract.md)
- Decision Records: [Decision Records](decisions/README.md)
- Governance docs: [Governance Documentation](governance/README.md)
- Evidence docs: [Evidence Documentation](evidence/README.md)
- Plans docs: [Plans Documentation](plans/README.md)
- History docs: [History Documentation](history/README.md)
- Terminal target design: [Terminal Governance Product Design](architecture/terminal-governance-product-design.md)
- Rule system: [Rules System](../rules/README.md)
- Skills: [Skills](../.agents/skills/README.md)
- Target package ontology: [Package Ontology](architecture/package-ontology.md)
- Boundary convergence: [Product Boundary Convergence](governance/product-boundary-convergence.md)
- Capability parity: [Capability Parity Ledger](governance/capability-parity-ledger.md)
- Repository profile contract: [Repository Profile Contract](governance/repository-profile-contract.md)
- Config boundary model: [Config Boundary Model](governance/config-boundary-model.md)
- Adopter boundary and retirement: [Adopter Boundary And Retirement](governance/adopter-boundary-and-retirement.md)
- Current package migration state: [Product Ontology](architecture/product-ontology.md)
- Distribution: [Distribution](architecture/distribution.md)
- Protocol contracts: [Protocol Contracts](architecture/protocol-contracts.md)
- Agent projections: [Agent Projections](architecture/agent-projections.md)
- Adoption profiles: [Adoption Profiles](architecture/adoption-profiles.md)
- Fleet and adopters: [Fleet And Adopters](architecture/fleet-and-adopters.md)
- Gate runner: [Gate Runner](architecture/gate-runner.md)
- Local state: [Local State](architecture/local-state.md)
- Generated artifact topology: [Generated Artifact Topology](architecture/generated-artifact-topology.md)
- Documentation topology: [Documentation Topology](architecture/docs-topology.md)
- MCP server: [MCP Server](architecture/mcp-server.md)
- Runner and mutation boundary: [Runner And Mutation](architecture/runner-and-mutation.md)
- Schema validation: [Schema Validation](architecture/schema-validation.md)
- Commit signatures: [Commit Signature Policy](governance/commit-signature-policy.md)
- Conversation requirements: [Conversation Ledger](governance/conversation-ledger.md)
- Adapter lifecycle: [Adapter Lifecycle](governance/adapter-lifecycle.md)
- Evidence and provenance: [Provenance And Attestation](governance/provenance-and-attestation.md)
- Docs registry: [Docs Registry](governance/docs-registry.md)
- OpenSpec governance: [OpenSpec Governance](governance/openspec-governance.md)
- Playbooks and skills: [Playbooks And Skills](governance/playbooks-and-skills.md)
- Release governance: [Release Governance](governance/release-governance.md)
- Standards adoption: [Standards Adoption Policy](governance/standards-adoption-policy.md)
