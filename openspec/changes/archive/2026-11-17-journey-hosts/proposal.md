# Proposal

## Why

DR-0021 declares three journeys for 0.2.0: installation through Mise from the published release
on macOS arm64, Linux x64 and Linux arm64. The hosted journey runs two of them. The pipeline model
selects the journey's legs from the release legs whose host is `linux-x64` or `macos-arm64`, so a
release run publishes the Linux arm64 archive and no journey installs it. DR-0021 names this gap in
its context, and the release candidate's clock starts only after a beta's journeys pass on every
declared host.

The archived `rc-plan` design gives the Linux arm64 leg in appendix B.6 and orders it as Change 10
of appendix B.8, after the record that succeeds DR-0015, which is DR-0021, and after the hermetic
journey. The archived `rc-scope-plan` design places it in the batch of 2026-11-28, with the
hermetic journey.

## What Changes

- The pipeline model names the journey's hosts as one list: `linux-x64`, `linux-arm64` and
  `macos-arm64`. The journey job of a release run, and of a journey dispatch, gains the Linux
  arm64 leg on the forge's native arm64 runner.

Not breaking: no input, job name or artifact of the existing legs changes. A release run and a
journey dispatch need one more passing leg.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: one added requirement, `The hosted journey runs on every declared host`.

## Impact

`.config/ci/pipeline.cue` and the workflow generated from it, `.github/workflows/ci.yml`; the pin
in `tests/architecture/ci/test_release_journey.py`; `openspec/specs/distribution/spec.md` through
this Change's delta, and `CHANGELOG.md`. No tool and no product module changes: the journey reads
its host from the platform it runs on. The second forge's pipeline does not change.

Out of scope: a Windows journey, which DR-0021 places after 0.2.0, and the journey's two stages,
which are the hermetic journey's.
