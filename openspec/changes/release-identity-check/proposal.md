# Proposal

## Why

The release assembler admits a platform upload when the upload's host, digests and product version
match. It never checks that the bytes came from the tagged commit, or that they carry the tag's
distribution version, although every leg's smoke record names both. Today only one thing keeps
other bytes out: the publish job downloads the uploads of its own run. A development build of the
same product version, or an upload from another commit, would pass every check the assembler makes.
Both reviews of the release-rehearsal draft found this gap.

## What Changes

- The publish step passes the release head to the assembler with `--expect-head`.
- The assembler admits a leg only when its smoke record's `source_commit` is that head and its
  `distribution_version` is the PEP 440 form of the tag's version. Any other leg refuses the
  release with `release_assets_identity_mismatch:<host>`. A head that is not a full commit ID
  refuses with `release_assets_head_invalid`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: release assembly admits only the tagged commit's bytes at the tag's version.

## Impact

- `tools/ci/delivery/release_assets.py` and its tests.
- `.config/ci/pipeline.cue` and its projection `.github/workflows/ci.yml`.
- Out of scope: what the build admits. Tag admission and the signed tag stay as they are.
