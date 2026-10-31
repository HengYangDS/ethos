# Proposal

## Why

GitLab checks every checkout against the input manifest of its bound supply image, and
`supply-currency` changed seven of the eight files that the manifest hashes. The bound image was
built from `c36790cd8`, so GitLab refuses the landed head until an image built from it is bound. The
hosted `supply_image` workflow built that image from `dev` at `16a43a623`.

`v0.2.0-alpha.22` was never tagged: on 2026-10-31 the release audit blocked the tag on advisories
that `supply-currency` fixes. The notes recorded since the entry was prepared therefore belong to
that entry.

## What Changes

- Bind
  `ghcr.io/hengyangds/ethos-ci-supply@sha256:d821c4f7768ca4ed5b9a8b55826f0a9e601f1c74a473a477d20be93bf584eb0a`
  in `.config/ci/pipeline.cue` and regenerate `.gitlab-ci.yml`.
- Fold the Unreleased notes into the `0.2.0-alpha.22` entry and restate its Security notes from the
  release audit of the landed head.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This binds a supply and prepares release notes, so `skip_specs: true` applies.

## Impact

`.config/ci/pipeline.cue`, the generated `.gitlab-ci.yml` and `CHANGELOG.md`. No lock or product
code changes.
