# Proposal

## Why

GitHub run 41728732273, `dev`'s run of `67ecc8727`, failed its Windows on Arm job before any test.
`tools/ci/toolchain/native.py` verifies the staged Mise executable by running it and then replaces
the cached executable with it, and Windows still held the file (`WinError 32`). The same job passed
on the same commit in proposal run 41713822013, so the failure says nothing about the commit, yet
it costs a rerun and delays a tag. The disposition is
`build/evidence/hosted-ci/github-41728732273-windows-arm-bootstrap-20261104.md`.

## What Changes

- The Mise bootstrap retries the replace of its staged executable while Windows reports that the
  file is held, waiting about 13 seconds at most; any other error, or a hold that outlasts the
  wait, fails as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. ETHOS's own CI tool bootstrap changes, so `skip_specs: true` applies.

## Impact

`tools/ci/toolchain/native.py`, `tests/unit/ci/test_mise_executable_supply.py` and `CHANGELOG.md`.
