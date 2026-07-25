---
subject: ethos:target-package-ontology
role: explanation
state: canonical
relations:
  canonical_for: target product package topology
---

# Package Ontology

The repository contains the buildable product package homes.

No active product migration host remains in `packages/`.

The current Python product package ontology is:

```text
packages/ethos-core
packages/ethos
```

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

## Target Packages

### `ethos-core`

Pure kernel and product contracts. Owns Authority, Subject, Commitment,
Change, Evidence, Claim, Chronicle, PlanIR contracts, state-machine
primitives, result envelope primitives, schema contracts, rule contracts,
quality semantics, determinism semantics, gate semantics, and proof-policy
semantics.

Forbidden: CLI parsing, public UX rendering, Git/OpenSpec/SQLite/process
execution, hosted forge execution, MCP/ACP projection execution, repository
mutation orchestration, pytest fixture hosting as runtime behavior,
adopter-specific semantics, and provider-specific ownership.

### `ethos`

Public runtime and CLI package. Owns the command tree, UX composition,
human-readable rendering, JSON output routing, repository lifecycle
orchestration, adapters, assistant/context projections, maintainer surfaces,
and local proof execution. Test fixtures remain under `tests/` and are not
shipped as product runtime.

The package is allowed to execute tools and adapt providers, but it must not
become the semantic center. Product semantics still derive from `ethos-core`,
tracked repository truth, system contracts, docs, OpenSpec records, evidence,
and Git facts according to the authority order.

### `distributions/npm`

Thin npm launcher adapter over the Python command plane. It is not part of the
Python product package ontology and must not own product semantics.

### `extensions/<extension-id>`

An extension bundle owns an ecosystem integration that must remain outside the
two buildable product packages. Each bundle declares its boundary in
`extension.toml` and keeps its local documentation, adapters, and focused tests
together. Extensions do not become product truth centers, dynamic package
imports, or adopter prerequisites by existing in the repository.

No extension bundle is currently shipped. In particular, independent
verification keeps only its provider-neutral product contract; provider-run
verifier and pre-receive executables are operator-owned and out of tree. No
root-level generic adapter directory is part of the product topology.

## Retired Product Package Families

Earlier product designs used separate Python package homes such as
`ethos-contracts`, `ethos-quality`, `ethos-repository`, `ethos-assistants`,
`ethos-adapters`, and `ethos-test`. Those names now describe semantic areas
inside the two-package topology; they are not active package homes.

Historical references to those package names are stale unless explicitly marked
as history. Promoted docs, tests, quality_summarys, and release checks should use the
active topology above.

## Boundary Rule

A new package is justified only when it owns a distinct semantic obligation that
cannot be kept clearer inside `ethos-core` or `ethos`. Split for durable meaning,
not for temporary implementation convenience.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
