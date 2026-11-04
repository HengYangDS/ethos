# Proposal

## Why

The repository's Mise configuration locks uv, which runs every local and supply image command. The
GitHub projection installs uv with `astral-sh/setup-uv` in three places, and
`.config/ci/pipeline.cue` names its version there as the literal `"0.13.6"`. A uv upgrade therefore
edits four carriers, and a missed literal makes hosted CI run a different uv than every other path.

- The upgrade to uv 0.13.7 on 11-04 is the next such edit.

## What Changes

- The CI model takes the version of each uv setup step from the uv that the Mise configuration
  declares, through the projection input that already supplies its Node version.
- That input is renamed from `node` to `mise`, after the configuration it binds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: hosted uv setup installs the uv that the Mise configuration declares.

## Impact

`.config/ci/pipeline.cue`, `.config/checks/ci-projection/policy.toml`, the architecture tests that
read that input, and the changelog. The generated projections do not change.
