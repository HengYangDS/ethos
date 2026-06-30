---
subject: ethos:package-ontology
role: decision
state: canonical
relations:
  canonical_for: package topology
---

# Product Ontology

ETHOS keeps one thin command package, five semantic Python product packages,
and separate distribution adapters:

```text
ethos
ethos-kernel
ethos-project
ethos-governance
ethos-workspace
ethos-agent
ethos-node
```

Top-level packages are cohesive product families:

- `ethos`: public command plane and UX composition.
- `ethos-kernel`: pure models, result envelope, and action graph algebra.
- `ethos-project`: init, adopt, scaffold, profile, and fleet inspection.
- `ethos-governance`: commitments, schemas, claims, evidence, standards,
  release readiness, and self-evolution.
- `ethos-workspace`: local state, gate execution, lanes, land, and publish
  boundaries.
- `ethos-agent`: assistant, MCP, ACP, context, and playbook projections.
- `ethos-node`: npm launcher adapter for the public command plane.

Adopter-specific semantics stay in adopter profiles and repositories. Product
packages may expose adapters, but they do not hardcode adopter private names.
Distribution adapters are not new truth centers; they forward to the Python
command plane.
