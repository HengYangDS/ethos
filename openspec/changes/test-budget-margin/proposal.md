# Proposal

## Why

`test-budget-densify` brought `python_tests` to 94,849 effective lines, under the 95,000 ceiling.
Two more lanes land after this one and add about 109 test lines, which would leave the repository
11 lines under its ceiling. Six test modules that no other open lane touches still spread
signatures, calls and parametrize lists over one line per element only because of a magic trailing
comma, although each fits on one line.

## What Changes

- In those six modules, the magic trailing commas of constructs that fit on one line go, so the
  repository's own formatter writes each construct on one line. Nothing else changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `tests/unit/openspec/lifecycle/test_archive_transition_public_recovery.py`,
  `tests/unit/adapters/repo/commit/test_admission.py`,
  `tests/unit/lanes/retirement/test_linked_public_boundaries.py`,
  `tests/unit/adoption/quality/test_python_evidence.py`,
  `tests/unit/release/test_release_identity_admission.py` and
  `tests/unit/projection/test_verification_model.py`.
