# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.20` lacks three repairs that the
accepted `dev` carries:

- `reference-grammar-owners`: prewrite no longer refuses at least 18 references in governed
  repositories that no executor runs or that a declaration supplies.
- `windows-arm64-delivery`: a release can serve `windows-arm64` through the x64 runtime that
  Windows on Arm emulates. DDWG's GitLab Windows runner needs it.
- `release-path-repairs`: a repository formed by `ethos adopt --create` gains `main` at its first
  `accepted_ff` closeout, and a version bump no longer changes a dependency lock.

ETHOS's own GitLab verification refuses every checkout since `0.2.0-alpha.20`, because its bound
supply image hashes a lock that the old workspace changed.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.21`. No lock or test changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.21` entry. It describes every user-visible
  product change since `v0.2.0-alpha.20` and the known advisories in the release's shipped bytes.
- `.config/ci/pipeline.cue` binds the supply image built from the landed `release-path-repairs`
  head, and `ethos lane project` regenerates `.gitlab-ci.yml`. That image's inputs match the
  release checkout, because the version bump changes none of them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is release preparation; `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `CHANGELOG.md`, `.config/ci/pipeline.cue` and the
generated `.gitlab-ci.yml` change. Product behavior does not change.
