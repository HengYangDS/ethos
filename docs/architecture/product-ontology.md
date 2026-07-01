---
subject: ethos:package-ontology
role: decision
state: canonical
relations:
  canonical_for: package topology
---

# Product Ontology

Status: canonical.

Purpose: summarize the current physical product packages and distribution
adapters.

See also: [Package Ontology](package-ontology.md) and
[Command Plane](../reference/command-plane.md).

This page summarizes the current product package state. The detailed ontology
is [Package Ontology](package-ontology.md).

Current product packages are:

```text
ethos-core
ethos-contracts
ethos-quality
ethos-repository
ethos-assistants
ethos-adapters
ethos
ethos-test
```

No active product migration host remains in `packages/`. `ethos` is the public
CLI package and composes the target packages without importing retired host
modules.

Adopter-specific semantics stay in adopter profiles and repositories. Product
packages may expose adapters, but they do not hardcode adopter private names.
Distribution adapters are not new truth centers; they forward to the Python
command plane.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
