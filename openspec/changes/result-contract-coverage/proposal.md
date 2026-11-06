# Proposal

## Why

ETHOS's combined branch coverage sits at its 95% floor. The `mise-lock-module` proof blocked
`unit-architecture` at 94.98% with every test passing. The result contract adds about 420 source
lines, and no test reaches several of its refusals: the bound moving small entries once
trimming the failing gaps is not enough, detail that parses but does not match, missing detail,
a stale detail file that cannot be removed, an unresolvable detail store, and a next action that
does not split.

## What Changes

- Tests specify those refusals through the public readers: `apply_payload_budget`,
  `expand_result`, `derive_next_step` and `emit`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `tests/unit/kernel/test_result_bound.py`, `tests/unit/kernel/test_result_next_step.py` and
  `tests/unit/surface/cli/test_output.py`.
