# Proposal

## Why

`v0.2.0-alpha.22` bounds only Python and Markdown files. `cross-language-size`, which the owner
asked for on 2026-10-31, bounds every authored code file by one ceiling, and adopters install only
published releases.

`cross-language-size` also changed `uv.lock`, one of the eight inputs that the GitLab supply image
hashes, so GitLab refuses the landed head until an image built from it is bound. The hosted
`supply_image` workflow built that image from `dev` at `c7388afd9` (run 41170871592) and pushed
`ghcr.io/hengyangds/ethos-ci-supply@sha256:3983dae4b8bbdf6112e6d7035e0825cb52d5ab0c9f236a9ba5596abc9f99f433`.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.23`. No lock or test changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.23` entry. It describes every user-visible
  product change since `v0.2.0-alpha.22` and the known advisories in the release's shipped bytes.
- `.config/ci/pipeline.cue` binds the new supply image, and `.gitlab-ci.yml` is regenerated from it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release and binds a supply, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `CHANGELOG.md`, `.config/ci/pipeline.cue` and the
generated `.gitlab-ci.yml`. No lock or product code changes.
