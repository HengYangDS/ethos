# Proposal

## Why

Since `result-contract` landed, every JSON result over its budget is bounded: `data` keeps only its
small entries, and the full result sits in a digest-bound detail file. The hosted verification
receipt reads the executed host proof's file directly, and that proof is always over budget, so its
`data.checks` is no longer inline. GitLab pipeline 14451 on dev `bfaa87543` therefore refused with
`invalid_hosted_observation:'checks'`, `hosted_test_report_invalid` and
`hosted_coverage_report_invalid`.

## What Changes

- The receipt reads the full result through `ethos.result.expand_result`, which verifies the
  detail file against the digest and size the bounded result names. A result that was never
  bounded is read as it is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `tools/ci/hosted_verification.py` and `tests/unit/ci/test_hosted_verification.py`.
