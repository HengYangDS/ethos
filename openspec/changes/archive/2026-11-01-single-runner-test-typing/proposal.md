# Proposal

## Why

`test-runner-unification` added `tests/architecture/test_single_test_runner.py`, whose search seeds
its work list with the session's parsed module. ty infers that list as `list[Module]`, so extending
it with the function definitions the search reaches is an `invalid-argument-type` error, and the
lane proof stopped at the `python-types` gate with one violation.

## What Changes

- The search declares its work list as `list[ast.AST]` and its seen set as `set[str | None]`, the
  element types that the module and the reached functions share. The test keeps its assertion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The test keeps its assertion, so `skip_specs: true` applies.

## Impact

`tests/architecture/test_single_test_runner.py` only.
