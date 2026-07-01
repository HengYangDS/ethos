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

Current migration-host packages remain active, but the target product package
homes now also exist as buildable packages:

```text
ethos-core
ethos-contracts
ethos-repository
ethos-assistants
ethos-adapters
ethos
ethos-test
```

Migration-host packages are not the final product ontology:

```text
ethos-kernel
ethos-project
ethos-governance
ethos-workspace
ethos-agent
ethos-node
```

Current migration-host packages are:

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

`ethos` is the target public CLI package. During migration it may temporarily
bridge to migration-host modules, but it is not itself a migration host.

Target packages are the semantic destination for new product work. The current
state is `in_progress`: physical target homes exist, but migration is not
complete while migration hosts still carry active behavior. Migration hosts
remain available until capability parity, shadow parity, and retirement
decisions prove that their contents can be moved or frozen safely.

Adopter-specific semantics stay in adopter profiles and repositories. Product
packages may expose adapters, but they do not hardcode adopter private names.
Distribution adapters are not new truth centers; they forward to the Python
command plane.
