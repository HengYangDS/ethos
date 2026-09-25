---
subject: docs:architecture
role: index
state: canonical
relations:
  canonical_for: architecture documentation navigation
---

# Architecture

Status: canonical navigation, not a second architecture contract.

Purpose: route readers from a product question to the explanation that owns it.

See also: [Documentation Root](../README.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Command Plane](../reference/command-plane.md).

## Product Reach

- [Adoption profiles](adoption-profiles.md) and [fleet boundaries](fleet-and-adopters.md): how repositories join without copying ETHOS's layout.
- [Distribution](distribution.md), [MCP server](mcp-server.md), and [agent projections](agent-projections.md): how users and agents reach the same product meaning.
- [Protocol contracts](protocol-contracts.md): what extension consumers may depend on.

## Execution And Trust

- [Runner and mutation](runner-and-mutation.md), [transition plan](transition-plan.md), and [local state](local-state.md): intent-to-effect boundaries and recovery.
- [Gate runner](gate-runner.md): how one quality decision reaches execution.

## Derived Structures

- [Declarative governance compiler](declarative-governance-compiler.md) and [generated artifact topology](generated-artifact-topology.md): which declarations own projections.
- [Schema validation](schema-validation.md): where structural contracts are checked.
