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

Purpose: summarize the current physical product packages and distribution
adapters. The detailed package boundary is [Package Ontology](package-ontology.md).

Current Python product packages are:

```text
ethos-core
ethos
```

`ethos-core` owns pure kernel, contract, quality, and proof-policy semantics.
`ethos` owns the public runtime, command plane, repository orchestration,
adapters, and assistant projections. Test fixtures remain under `tests/`,
outside the shipped product package.

Retired names such as `ethos-contracts`, `ethos-quality`, `ethos-repository`,
`ethos-assistants`, `ethos-adapters`, and `ethos-test` now describe semantic
areas inside the two package homes; they are not active package homes.

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
