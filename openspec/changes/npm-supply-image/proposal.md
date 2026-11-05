# Proposal

## Why

GitLab pipeline 14172 for the proven beta.2 head `e4080fbc9` failed in `ethos:commit-policy`. The
job checks the supply image's manifest first, and `sha256sum --check` found that
`package-lock.json` differs from the lock that the bound image
`ethos-ci-supply@sha256:d0eef172…` was built from. `npm-advisory-move` changed the lock to npm
12.2.2, but the GitLab jobs still select the image built from the npm 12.2.1 lock.

## What Changes

- The hosted `supply_image` workflow builds an image from this lane's lock, and every GitLab supply
  job selects its digest.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Binding a rebuilt image changes no requirement, so `skip_specs: true` applies.

## Impact

`.config/ci/pipeline.cue` and its generated `.gitlab-ci.yml`.
