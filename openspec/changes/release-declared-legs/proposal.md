# Proposal

## Why

Both Windows legs of release run 42117725176 failed before their upload step, so beta.3 published
without Windows runtimes. The assembler reads only the artifacts that legs uploaded, and an
optional leg that fails uploads nothing. As a result `left-out.json` stayed empty and the release
notes did not name the missing platforms, although the beta.3 changelog promises that they would.
The notes were amended by hand after publication.

Which legs are optional is also stated in two places that must agree by hand:

- `_REQUIRED` in `tools/ci/delivery/release_assets.py`;
- `startsWith(matrix.host, 'windows')` in the release workflow's `continue-on-error`.

## What Changes

- Each entry of `releaseLegs` in `.config/ci/pipeline.cue` declares whether its platform is
  required. Two things derive from that declaration:
  - the release workflow's `continue-on-error`;
  - the assembler's `--required` and `--optional` host lists.
- The assembler refuses three cases:
  - a missing required platform, with `release_assets_platform_missing`, as before;
  - an artifact for a platform the legs do not declare, with `release_assets_host_undeclared:<host>`;
  - an unknown or doubly declared host, with `release_assets_hosts_invalid`.
- Every declared optional platform that the release does not publish enters `left-out.json` with its
  cause: `leg_incomplete` when the leg uploaded nothing, or `inventories_incomplete` when its
  inventories were incomplete.
- The release notes name those platforms and tell adopters what to do: an adopter that installs
  ETHOS on them from its Mise declaration keeps its current release until a later release publishes
  them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a release names each declared platform that it does not publish.

## Impact

- `.config/ci/pipeline.cue` and its projection `.github/workflows/ci.yml`.
- `tools/ci/delivery/release_assets.py`, its unit tests and the CI projection tests.
- Out of scope: making Windows required, and any change to which platforms the release builds.
