## Why

Different source trees, wheels, and runtimes have reused `0.1.0a2`; package
ordering and installed-runtime identity are therefore ambiguous.

## What Changes

- Derive Python/npm metadata from one tracked product version.
- Separate product, distribution, source, artifact, and runtime identity.
- Give unreleased builds comparable PEP 440 commit/tree identities; reserve the
  exact version for admitted releases.
- Reject rollback, reuse, and source/artifact/tag/manifest disagreement.
- **BREAKING**: `0.1.0a2` remains historical only and can no longer be emitted as
  a current ETHOS package or runtime.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: product, distribution, source, artifact, and runtime identity
  become explicit, immutable, and consistently projected.
- `command-plane`: public version inspection becomes structured and
  source-independent.

## Impact

Package metadata/build hooks, release admission, runtime currentness, CLI JSON,
tests, and release docs change. Forge releases remain projections.
