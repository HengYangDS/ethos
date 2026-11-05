# Proposal

## Why

The full proof of `ce07eb7c9` blocked at once on `repository_paradigm_code_size`:
`tests/unit/cli/test_refresh_archive_public_coverage.py` has 520 effective lines, over the 500-line
ceiling. `cause-preserving-results` added its policy-refusal compensation test to a file that was
already close to the limit, and the refresh merge kept that test.

## What Changes

- The archive command's compensation and failure-recovery tests move to their own module,
  `tests/unit/cli/test_archive_compensation.py`. That module covers what happens when an archive
  effect fails or is refused partway through. The original module keeps admission, preflight,
  coordinates, collisions and readiness. No test changes what it asserts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Moving tests between modules changes no requirement, so `skip_specs: true` applies.

## Impact

`tests/unit/cli/test_refresh_archive_public_coverage.py` and the new
`tests/unit/cli/test_archive_compensation.py`.
