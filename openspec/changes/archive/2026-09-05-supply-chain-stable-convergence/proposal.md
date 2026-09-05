## Why

Several repository-controlled dependencies and execution images trail stable
upstream releases even though ETHOS requires every controlled direct input to
resolve to the current stable release. The repository needs one bounded
convergence pass so its declarations, locks, immutable digests, generated CI
projections, built package, and installed runtime agree again.

## What Changes

- Advance each stale direct Python and Node dependency to its verified stable
  release and regenerate the existing lockfiles through their native package
  managers.
- Advance the single product-version authority to `0.2.0-alpha.4` so the new
  accepted runtime does not reuse the prior prerelease identity.
- Advance the uv package and CI runtime image to the verified stable release
  and immutable digest, then materialize provider files from their existing
  templates.
- Make an exact target source checkout's root lock-current `.venv` own its
  build backend, locked uv execution, and dependency-byte supply so an older
  selected runtime can activate newer accepted source without carrying that
  source's development closure.
- Preserve already-current Node compatibility releases, downloaded tools, and
  GitHub Action commits without churn.
- Verify official OpenSpec behavior, the complete quality gate set, package
  construction, package-only installation, and immutable runtime identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: The repository-locked official OpenSpec identity
  advances from 1.11.0 to the verified stable 1.12.0 release.
- `distribution`: Source runtime construction verifies the target checkout's
  build closure while continuing to export only its production closure.
- `runtime-activation`: Source activation separates the older invoking
  runtime from the exact target checkout environment that owns build and
  dependency supply.

## Impact

The change updates `VERSION`, existing dependency manifests and locks, the
OpenSpec runtime contract and version expectations, CI template owners and
generated provider projections, and tests that assert those identities. It
creates no second version authority, compatibility layer, or host-managed
installation.
