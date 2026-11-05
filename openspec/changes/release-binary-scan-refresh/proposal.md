# Proposal

## Why

This lane's `release-inventory` and `release-binary-scan` Changes are archived. Refreshing the lane
onto the candidate, which now carries 0.2.0-beta.2 and `repository-exit`, conflicted in three
files:

- `CHANGELOG.md`: this lane's Unreleased notes against the new 0.2.0-beta.2 entry;
- `.config/ci/pipeline.cue` and the generated `.gitlab-ci.yml`: both sides bound a different supply
  image. This lane's image (`2f71a037`) carries Grype but npm 12.2.1. The candidate's (`212d1715`)
  carries npm 12.2.2 but not Grype. Neither matches the merged locks.

## What Changes

- The merge keeps both changelog sides. The lane's notes stay under `## [Unreleased]`.
- The image conflict resolves to the candidate's digest only to complete the merge. Then a supply
  image built from the merged locks, with Grype and npm 12.2.2, is bound.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A merge and a rebind change no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `.config/ci/pipeline.cue` and `.gitlab-ci.yml`.
