---
subject: ethos:target-package-ontology
role: explanation
state: canonical
relations:
  canonical_for: target product package topology
---

# Package Ontology

ETHOS has one buildable Python product package:

```text
src/ethos
```

The repository-root `pyproject.toml` is its sole distribution owner. Kernel,
contracts, quality, command, repository, adapter, and projection boundaries are
internal modules, not separately versioned products.

Non-Python distribution adapters do not belong to the Python product package
ontology. Distribution adapters use a separate layout:

```text
distributions/npm
```

Optional ecosystem integrations do not belong to either product package or the
distribution adapter layout. When shipped source is justified, they use declared
extension bundles:

```text
extensions/<extension-id>/
```

## Internal Boundary

Pure contracts and reducers must not import repository I/O, subprocess, SQLite,
hosted providers, or public rendering. Effects and provider integrations remain
at explicit composition boundaries. Tests live under `tests/` and are not
shipped as product runtime.

### `distributions/npm`

Thin npm launcher adapter over the Python command plane. It is not part of the
Python product package ontology and must not own product semantics.

### `extensions/<extension-id>`

An extension bundle owns an ecosystem integration that must remain outside the
product package. Each bundle declares its boundary in
`extension.toml` and keeps its local documentation, adapters, and focused tests
together. Extensions do not become product truth centers, dynamic package
imports, or adopter prerequisites by existing in the repository.

No extension bundle is currently shipped. In particular, independent
verification keeps only its provider-neutral product contract; provider-run
verifier and pre-receive executables are operator-owned and out of tree. No
root-level generic adapter directory is part of the product topology.

## Retired Product Package Families

Earlier product designs used separate Python package homes. Their concerns now
live as internal modules under `src/ethos`; they are not active package homes.

Historical references to those package names are stale unless explicitly marked
as history. Promoted docs, tests, status projections, and release checks should
use the active topology above.

## Boundary Rule

A new distribution is justified only by an independently versioned public
contract. Split for durable product meaning, not implementation convenience.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
