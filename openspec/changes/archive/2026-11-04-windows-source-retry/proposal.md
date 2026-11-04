# Proposal

## Why

The protected Windows runner of an adopter, DDWG, failed 2 of the 7 jobs that started less than 10
seconds after the previous job ended. Over 63 jobs since 2026-11-01, none of the 14 jobs that
started more than 60 seconds later failed. In both failures, GitLab's source checkout ran
`git clean` and met "Invalid argument" on the previous job's just-executed `.pyd` files, DLLs and
`node.exe`. Windows still held them, and the job failed before running anything.

## What Changes

- The common CI model, `.config/ci/verification.cue`, sets GitLab's native `GET_SOURCES_ATTEMPTS`
  to `"3"` on every Windows verification job it generates, so a transient source checkout failure
  retries before the job fails.
- A runner declaration cannot override the value, just as it cannot override `GIT_DEPTH`.
- The tool cache is not excluded from the clean, because reusing a cache across protected jobs
  would change the trust boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: generated Windows verification jobs retry their source checkout.

## Impact

`.config/ci/verification.cue` and `tests/unit/projection/test_verification_model.py`. Adopters
receive the change when they regenerate their projections after moving to the release that ships
it.
