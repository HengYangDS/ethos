# Proposal

## Why

Proof b10p2 of 2026-11-12 failed in `tests/architecture/test_decision_density.py`. The
`toolchain-lock-scope` Change raised the cognitive complexity of `toolchain_gaps` from 15 to 16,
past the threshold of 15, and lowered `repository_mise_files` from its pinned 16 to 15, so its pin
is stale. The baseline only shrinks: an improved function must leave it.

## What Changes

- `toolchain_gaps` moves the mise owner's two lock checks into `_lock_gaps`, so neither function
  exceeds the threshold. The rule and its gaps do not change.
- `repository_mise_files` leaves `tests/fixtures/decision-density-baseline.json`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Behavior is unchanged, so `skip_specs: true` applies.

## Impact

`src/ethos/repository/paradigm/toolchain.py` and `tests/fixtures/decision-density-baseline.json`.
