# Proposal

## Why

The readiness run on the archived `result-contract` head (`86f03fef0`) ran 28 gates in one pass and
refused two of them:

- `module-layout`: `tests/unit/cli/test_result_runtime.py` imports `runtime_identity` from its
  package root.
- `source-budget`: the Python tests total 95,012 effective lines, 12 over the terminal ceiling of
  95,000.

The ceiling policy asks to remove accidental complexity before any raise. Here the complexity is
test plumbing that `result-contract` made redundant.

## What Changes

- The runtime test imports `ethos.surface.cli.runtime_identity` by its full path.
- `full_payload=True` arguments that the new test-runner default makes redundant are removed, and
  the `expand_payload` wrapper gives way to `ethos.result.expand_result`.
- Two near-duplicate bound tests, which both check that a command's own `data` entries survive
  beside `bound`, become one parametrized test.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None, so `skip_specs: true` applies.

## Impact

- Tests and test support only: `tests/unit/cli/test_result_runtime.py`, `tests/support/ethos_cli_runner.py`,
  `tests/unit/kernel/test_result_bound.py`, and the modules whose calls carried a redundant
  `full_payload=True`.
- No production code, schema or rule changes.
