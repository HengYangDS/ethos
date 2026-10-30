# Proposal

## Why

The CI seed of the locked npm packages stops at 120 seconds (`tools/ci/toolchain/npm.py`). On the
emulated `windows-11-arm` host leg that seed took 108 seconds on `a2fdaa7d8` (run 40985443017) and
more than 120 seconds on `8f5bbbffa` (run 41014453956), where the deadline killed `npm ci` and the
required leg failed. The release's `windows-arm64` runtime leg runs the same seed, so the
`0.2.0-alpha.21` release would omit the archive that DDWG's Windows ARM64 runner needs.

## What Changes

- The npm seed's deadline becomes 600 seconds on every host. The seed stays bounded.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is CI tooling; `skip_specs: true` applies.

## Impact

`tools/ci/toolchain/npm.py` changes. No product, packaged or release-note change.
