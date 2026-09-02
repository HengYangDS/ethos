---
subject: ethos:decision:documentation-portability
role: decision
state: canonical
relations:
  current_owner: ../governance/docs-registry.md
---

# Documentation Portability

Status: canonical rationale. The Docs Registry and each repository's profile
own current behavior.

Purpose: preserve why portable documentation governance standardizes meaning
and discovery without standardizing every repository's physical tree.

See also: [Documentation Root](../README.md),
[Docs Registry](../governance/docs-registry.md), and
[Historical Topology Contract](../history/docs-topology-contract-20260708.md).

## Context

An earlier ETHOS design required every governed repository to reproduce one
fixed documentation kernel, including directory-local indexes and lifecycle
shaped paths. That made path equality stand in for semantic equivalence. It also
created empty directories and marker READMEs in repositories whose native
documentation domains did not need them.

Removing all common structure would create the opposite failure: agents and
tools would have to infer document purpose, authority, and lifecycle from prose
or repository-specific convention. The portable obligation is therefore
semantic discovery, not a cloned directory tree.

## Decision

Portable documentation governance consists of one profile-declared docs root
plus the `subject`, `role`, `state`, and `relations` metadata understood by the
Docs Registry. Each repository chooses the physical structure that truthfully
expresses its own subject domains. ETHOS may therefore retain a
`docs/decisions/` boundary without requiring an adopter to copy it.

Lifecycle state is metadata, not a `current/` or `future/` directory. A README
exists only when it owns real navigation or a directory boundary; it is not a
marker. ETHOS audits its own physical documentation shape as a product concern,
while the portable registry audits adopter meaning and discoverability.

## Consequences

- A repository can reorganize documents without changing their semantic
  identities, provided the profile root, metadata, and links remain coherent.
- ETHOS cannot reject an adopter merely because it lacks ETHOS-specific roots
  such as `architecture/` or `decisions/`.
- Physical-layout regressions in ETHOS remain valid product defects, but they do
  not silently become adopter requirements.
- Empty directories, duplicate indexes, and marker-only READMEs have no
  portability value and are deleted.

## Rejected Alternatives

- **One fixed tree for every repository:** rejected because path equality does
  not prove semantic equivalence and forces empty or misleading carriers.
- **No shared documentation contract:** rejected because readers would again
  depend on memory, prose conventions, or repository-specific heuristics.
- **Lifecycle directories such as `current/` and `future/`:** rejected because
  they duplicate Git and document metadata as mutable state authorities.

## Evidence

- [Docs Registry](../governance/docs-registry.md) defines the current portable
  metadata and directory-entrypoint rules.
- `src/ethos/repository/registry/docs/registry.py` resolves the profile-declared
  root and builds the semantic registry.
- `tests/unit/governance/test_docs_health.py` proves custom docs roots and
  repository-native layouts without requiring ETHOS's physical tree.
- [Historical Topology Contract](../history/docs-topology-contract-20260708.md)
  preserves the superseded fixed-tree context without making it current.

## Revisit And Retirement

Revisit if a real adopter demonstrates that profile-rooted metadata and native
links cannot provide deterministic discovery. Retire this record when the Docs
Registry's current owner itself preserves this decision's rejected alternatives,
consequences, and revisit trigger without becoming a second physical topology
authority.
