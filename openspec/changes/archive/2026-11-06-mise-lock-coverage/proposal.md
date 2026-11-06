# Proposal

## Why

The full proof of the archived `mise-lock-module` head blocked `unit-architecture` on coverage
alone: all 8,154 tests passed, but combined branch coverage was 94.98%, under the 95% floor. No test
reached two refusals in the new `mise_lock.py`: an unparseable lock, and a sidecar path that leaves
the repository.

## What Changes

- The toolchain tests exercise both refusals through `repository_mise_files`. They also cover two
  refusals no test reached in `mise.py`: a `settings` value that is not a table, and an aliased
  configuration, which carries no trust.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- `tests/unit/adapters/toolchain/test_mise_supply.py` and `test_mise.py`.
