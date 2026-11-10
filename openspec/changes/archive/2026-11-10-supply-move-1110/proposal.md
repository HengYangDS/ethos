# Proposal

## Why

The owner asked for every supply chain to move to its newest stable release. ETHOS last moved its
supply on 2026-11-09 (`supply-move-1109`). Against a cutoff of 2026-11-09T04:45:00Z, five
transitive npm packages and one CI action have newer stable releases.

## What Changes

- `package-lock.json` moves five transitive packages to their newest stable releases before the
  cutoff: `@eslint-community/regexpp` 4.12.3, `ansi-regex` 6.6.0, `follow-redirects` 1.16.3,
  `commander` 15.1.0 under `katex`, and `semver` 7.8.6.
- `docker/login-action` moves from v4.7.0 to v4.8.0 in `.config/ci/pipeline.cue` and its GitHub
  projection.
- The CI supply image is rebuilt from the moved lock and bound in `.config/ci/pipeline.cue`.

Already newest under the cutoff, and unchanged: both `uv.lock` files (`uv lock --upgrade` with the
cutoff resolves no change), every direct npm pin, every Mise tool, and the other six action pins.
Syft 1.57.1 and Grype 0.121.3 are stable but younger than the cutoff, so they wait for the next
move.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Locked versions change; no requirement changes.

## Impact

`package-lock.json`, `.config/ci/pipeline.cue`, `.github/workflows/ci.yml` and `.gitlab-ci.yml`
(the image binding).
