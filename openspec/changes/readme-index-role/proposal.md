# Proposal

## Why

A directory's README can carry any document role and any length. Docs health checks only that a
README exists where a directory has two or more children, that it has children, and that it routes
to one of them (`src/ethos/repository/registry/docs/health.py:296-319`), and the registry checks
only that its role is a known value. The rule text keeps a README that is "the actual index,
navigation entrypoint, or semantic boundary" (`docs/governance/docs-registry.md:274-276`) without
defining a boundary. So a governed repository's `docs/governance/README.md` grew into a 270-line
policy page over 33 commits while every check passed. Across the 12 governed repositories, 31 of 35
READMEs declare `role: index` (median 16, maximum 84 nonblank lines); the four others carry policy,
how-to, evidence and history.

## What Changes

- **Breaking:** every README that the docs registry admits declares `role: index` and holds its
  directory's purpose, scope and navigation, in at most 100 nonblank lines. Docs health reports
  `docs_readme_not_index:<path>` and `docs_index_too_long:<path>:<lines>>100`; both need authoring,
  so neither has an automatic repair.
- `docs/governance/docs-registry.md` drops "semantic boundary": a README's scope statement is part
  of its index, and policy, procedure, evidence and history live on named pages.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: ADDED requirement `A directory README is its index`.

## Impact

`src/ethos/repository/registry/docs/health.py`, its tests, `docs/governance/docs-registry.md` and a
CHANGELOG line. ETHOS's own registered READMEs all declare `role: index` and stay under the bound.
