# Design

## Context

See [proposal.md](proposal.md). `host-conformance` in `.config/ci/pipeline.cue` runs a 3 × 3
matrix of `ubuntu-latest`, `windows-latest` and `macos-latest` with Python 3.12 to 3.14 and adds
`windowsArmLeg` through `include`. The `release-platforms` job reuses `windowsArmLeg` for its
`windows-arm64` leg, which builds and qualifies the archive that a release declares for that host.
Durations in run 41713822013: Windows on Arm 70.8 min; `windows-latest` 43.6 to 51.0 min; quality
gates 35.3 min; Linux and macOS 10 to 16 min.

## Goals / Non-Goals

**Goals:**

- A proposal run no longer waits for the emulated Windows on Arm pair.
- Every accepted commit is still verified on Windows on Arm before it can be tagged.

**Non-Goals:**

- Native ARM64 CPython on Windows, which needs a `win_arm64` wheel from CEL upstream.
- The duration of the Windows x64 pairs, the next longest jobs.

## Decisions

- **Leave the pair to the accepted commit's run.** Landing fast-forwards `dev` to the proposal's
  exact commit, and `dev`'s run of that commit executes every commit-scoped job, so a Windows on Arm
  regression still fails a run of the commit before the release guide's tag step. Moving the pair
  only to the release run was rejected: a failure there comes after the tag.
- **Select the pair by the event.** The matrix `include` is a GitHub expression that yields no
  entry for a push of `refs/heads/proposal/*` and the Windows on Arm entry otherwise, using the
  same proposal-push condition as the run's concurrency group.

## Risks / Trade-offs

- [A regression specific to Windows on Arm lands] → `dev`'s run fails before any tag, and the fix
  lands as a new Change; the proposal runs of other lanes are unaffected.
