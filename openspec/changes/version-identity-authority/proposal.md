## Why

ETHOS has shipped semantically different source trees, wheels, and runtimes
under the reused `0.1.0a2` identity. Package managers therefore cannot compare
upgrades, runtime inspection cannot name the installed capability generation,
and artifact provenance is forced to compensate for a false product identity.

## What Changes

- Establish one tracked product-version authority and derive Python and npm
  distribution metadata from it rather than maintaining independent literals.
- Separate product version, distribution version, source identity, and artifact
  or runtime identity in public inspection and immutable manifests.
- Give every unreleased source build a unique PEP 440 identity derived from the
  next product version and exact source identity; accepted releases use the
  exact stable or prerelease version only after release admission.
- Reject version rollback, accepted-version reuse, same-version/different-source
  or bytes conflicts, and metadata/tag/manifest disagreement.
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

Python and npm package metadata, build hooks, release admission, hook runtime
manifests/currentness, CLI output, schemas, tests, and release documentation are
affected. Forge releases remain projections and do not become version authority.
