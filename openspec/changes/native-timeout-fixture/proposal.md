# Proposal

## Why

On 2026-11-12 the GitLab peer's hosted CI for `dev` at `d7131167d` failed one test,
`test_native_timeout_preserves_partial_output_and_owned_cleanup` in
`tests/unit/adoption/quality/native/test_nox.py`; GitHub's run 43173675185 passed at the same
commit. The test gives its Nox fixture a 15-second budget and expects the partial stdout to hold
`timeout-sentinel`. The fixture prints the sentinel only at the end of its static session, after
the behavior session's pytest run with coverage and the static session's Ruff run through
`ethos.domain.quality.nox`. On the loaded runner those two sessions used the whole budget: the
retained stdout ends with the coverage report and holds no sentinel.

## What Changes

- In the timeout variant, the behavior session writes its JUnit report, prints the sentinel and
  sleeps past the budget before it runs anything else. Only Nox's startup comes before the
  sentinel.
- The static session loses its timeout step, which the command no longer reaches.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

`tests/support/native_quality.py` only. The test, its budget and product code are unchanged.
