---
subject: ethos:target-package-ontology
role: decision
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

## Target Packages

### `ethos-core`

Pure kernel and product contracts. Owns Authority, Subject, Commitment,
Change, Evidence, Claim, Chronicle, action graph primitives, state machine
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
local proof execution, and product test fixtures.

The package is allowed to execute tools and adapt providers, but it must not
become the semantic center. Product semantics still derive from `ethos-core`,
tracked repository truth, system contracts, docs, OpenSpec records, evidence,
and Git facts according to the authority order.

### `distributions/npm`

Thin npm launcher adapter over the Python command plane. It is not part of the
Python product package ontology and must not own product semantics.

## Retired Product Package Families

Earlier product designs used separate Python package homes such as
`ethos-contracts`, `ethos-quality`, `ethos-repository`, `ethos-assistants`,
`ethos-adapters`, and `ethos-test`. Those names now describe semantic areas
inside the two-package topology; they are not active package homes.

Historical references to those package names are stale unless explicitly marked
as history. Current docs, tests, scorecards, and release checks should use the
active topology above.

## Boundary Rule

A new package is justified only when it owns a distinct semantic obligation that
cannot be kept clearer inside `ethos-core` or `ethos`. Split for durable meaning,
not for temporary implementation convenience.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
