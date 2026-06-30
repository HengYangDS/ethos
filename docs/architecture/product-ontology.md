---
subject: ethos:package-ontology
role: decision
state: canonical
relations:
  canonical_for: package topology
---

# Product Ontology

This page describes the current migration-host package state. The target
ontology is [Package Ontology](package-ontology.md).

Current packages are not the final product ontology:

```text
ethos
ethos-kernel
ethos-project
ethos-governance
ethos-workspace
ethos-agent
ethos-node
```

Current migration-host packages are:

- `ethos`: public command plane and UX composition.
- `ethos-kernel`: pure models, result envelope, and action graph algebra.
- `ethos-project`: init, adopt, scaffold, profile, and fleet inspection.
- `ethos-governance`: commitments, schemas, claims, evidence, standards,
  release readiness, and self-evolution. Its contents are expected to split
  across target contracts, repository semantics, and adapters.
- `ethos-workspace`: local state, gate execution, lanes, land, and publish
  boundaries. Its logical semantics move to repository semantics; provider
  implementations move to adapters.
- `ethos-agent`: assistant, MCP, ACP, context, and playbook projections. Its
  target home is `ethos-assistants` plus protocol adapters.
- `ethos-node`: npm launcher adapter for the public command plane. Its target
  home is `distributions/npm`.

Adopter-specific semantics stay in adopter profiles and repositories. Product
packages may expose adapters, but they do not hardcode adopter private names.
Distribution adapters are not new truth centers; they forward to the Python
command plane.
