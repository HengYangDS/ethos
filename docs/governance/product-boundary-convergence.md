---
subject: ethos:product-boundary-convergence
role: policy
state: canonical
relations:
  canonical_for: reference-adopter migration and retirement safety
---

# Product Boundary Convergence

Status: canonical.

Purpose: keep product truth, adopter truth, and adapter evidence in their own
repository boundaries.

See also: [Product Design Contract](product-design-contract.md) and
[Adopters](../architecture/fleet-and-adopters.md).

The ETHOS product repository is the product truth target. An adopter is bound
through its own profile and retains its own source, tests, docs, OpenSpec,
ChangeContracts, Attestations, and evidence. No adapter, projection, or
cross-repository observation
creates a shared task store or expands product ontology.

The safe lifecycle is:

```text
adopt -> status -> plan -> prove -> land -> publish
```

Use the public commands for the bound repository:

```bash
ethos adopt --root <repo> --json
ethos status --root <repo> --json
ethos plan --changed --json
ethos prove --root <repo> --full --json
```

A retirement or boundary decision requires current profile facts, an admitted
proof result, and repository-local evidence. MCP and skill projections may help
an agent observe the boundary, but they do not decide it.
