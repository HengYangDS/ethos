# Proposal

## Why

GitLab checks every checkout against the input manifest of its bound supply image, and
`probe-supply` changed three of the eight files that the manifest hashes: `uv.lock`,
`.config/mise/config.toml` and `.config/mise/mise.lock`. The bound image was built before that
Change, so GitLab refuses the landed head until an image built from it is bound. The hosted
`supply_image` workflow built that image from `dev` at `e5c63cd0e`.

## What Changes

- Bind
  `ghcr.io/hengyangds/ethos-ci-supply@sha256:f9a083b6dc5fb5ba293828c71e534a63927d8993ef3787b7121ccd3b2671e072`
  in `.config/ci/pipeline.cue` and regenerate `.gitlab-ci.yml`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This binds a supply, so `skip_specs: true` applies.

## Impact

`.config/ci/pipeline.cue` and the generated `.gitlab-ci.yml`. No lock, product code or release entry
changes.
