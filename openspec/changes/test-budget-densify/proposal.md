# Proposal

## Why

The full proof of the archived `result-contract-coverage` head blocked `source-budget` with
`source_budget_terminal_exceeded:python_tests:95115>95000`. The test tree passed its 95,000-line
terminal ceiling after the result contract and the mise coverage tests landed. The ceiling policy
removes accidental complexity first; several modules repeat the same multi-line call or assertion
run, which one local helper or one tuple assertion expresses once.

## What Changes

- Repeated calls in test modules move into one module-local helper each, and runs of field
  assertions become one tuple assertion. Every test keeps its behavior and its assertions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- Test modules under `tests/unit/adoption/`, `tests/unit/cli/`, `tests/unit/kernel/`,
  `tests/unit/mutation/`, `tests/unit/repository/policy/` and `tests/architecture/`.
