---
subject: ethos:package-ontology
role: explanation
state: canonical
relations:
  canonical_for: package topology summary
  derives_from: docs/architecture/package-ontology.md
---

# Product Ontology

Status: canonical.

Purpose: summarize the current physical product package and distribution
adapters. The detailed package boundary is [Package Ontology](package-ontology.md).

The Python product package is:

```text
src/ethos
```

It owns the semantic kernel, contracts, quality policy, command plane,
repository orchestration, adapters, and assistant projections. Those concerns
remain internally bounded but share one version and one distribution identity.
Test fixtures remain under `tests/`, outside the shipped product package.

Retired names such as `ethos-contracts`, `ethos-quality`, `ethos-repository`,
`ethos-assistants`, `ethos-adapters`, and `ethos-test` now describe semantic
areas inside the product package; they are not active package homes.

Non-Python distribution adapters are separate projections:

```text
distributions/npm
```

Distribution adapters are not truth centers; they forward to the Python command
plane.

Adopter-specific semantics stay in adopter profiles and repositories. Product
packages may expose adapters, but they do not hardcode adopter private names.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
