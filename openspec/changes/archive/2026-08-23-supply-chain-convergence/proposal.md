## Why

ETHOS controls versions across Python, Node, downloaded binaries, container
images, and hosted-CI actions, but several values are duplicated between native
owners, installer defaults, and generated provider files. That permits stale
or orphaned pins and makes a repository-wide "latest stable" claim impossible
to prove mechanically.

## What Changes

- Define one semantic owner for every controlled direct dependency or external
  tool and classify lockfiles, checksums, generated workflows, and documentation
  as checked projections.
- Upgrade every controlled direct input to the current stable release resolved
  by its native package manager or authoritative upstream, with exact locks,
  action SHAs, image digests, and downloaded-binary checksums.
- Make supply-chain proof detect duplicate owners, projection drift, orphaned
  controlled literals, and direct-bound/lock disagreement.
- Remove installer defaults and provider-local version literals when the
  existing declaration owner can supply the value.
- Keep repository governance and release evidence in ETHOS; do not introduce a
  second dependency resolver, environment manager, update ledger, or runtime
  authority.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: Strengthen the quality contract with complete, uniquely owned,
  current, integrity-bound supply-chain declarations and checked projections.

## Impact

This change affects Python and Node dependency declarations and locks, external
tool policy, release/SBOM tooling, CI templates and generated provider files,
installer scripts, and their architecture and regression tests. It does not
adopt mise, Pixi, Renovate, or another workflow or environment authority; those
remain replacement candidates only when a separate atom proves net deletion.
