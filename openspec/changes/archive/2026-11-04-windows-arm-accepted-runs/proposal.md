# Proposal

## Why

A Work Lane lands only after both Forges verify its proposal, so the slowest job of a proposal run
sets the wait of every landing. On GitHub that job is the Windows on Arm host conformance, which
runs the x64 CPython 3.14 that Windows emulates because CEL ships no `win_arm64` wheel. In run
41713822013, the proposal run of `67ecc8727`, it took 70 minutes 46 seconds; the slowest native
pair, `windows-latest / Python 3.14`, took 51 minutes and the quality gates 35 minutes.

The landed commit is the proposal's exact commit, and `dev`'s run of that commit runs every
commit-scoped job again before the release guide lets it be tagged. Windows on Arm therefore keeps
a verification per accepted commit when it leaves the proposal run. The 11-04 strategy report
left this move to the owner, who delegated the decision to the agent on 2026-11-04.

## What Changes

- A push of a proposal ref runs GitHub's host conformance on Linux, macOS and Windows x64 with
  Python 3.12, 3.13 and 3.14, without the Windows on Arm pair.
- Every other run that verifies a commit keeps the Windows on Arm pair: a push of `dev`, a pull
  request and a manual dispatch. The release run's `windows-arm64` leg is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: "Each Forge verifies a published commit once" names the one job that a proposal push
  leaves to `dev`'s run of the landed commit.

## Impact

`.config/ci/pipeline.cue` and its projection `.github/workflows/ci.yml`,
`tests/unit/ci/delivery/test_release_publication.py`, the quality specification and
`CHANGELOG.md`. GitLab runs no Windows job, and adopters' CI models are their own.
