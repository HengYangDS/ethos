# Proposal

## Why

When every test passes but the combined coverage is below the floor in
`.config/checks/coverage/coverage.toml`, pytest-cov exits non-zero and the behavior gate reports
`quality_behavior_tests_failed`. On 2026-11-06 at 22:05 a full proof failed that way at 94.98
percent against a floor of 95, and the gap sent the reader to look for a failing test that did not
exist. The 2026-11-07 expert committee (R11) names `coverage-floor-gap`: the floor gets its own gap.

## What Changes

- A run whose tests all pass but whose measured combined coverage is below the declared floor
  blocks with `quality_behavior_coverage_below_floor`, decided as coverage.py decides it: rounded to
  the declared precision, and a floor of 100 only by an exact 100.
- The coverage evidence records the floor beside the measurement.
- A failing or missing test still reports `quality_behavior_tests_failed`; nothing changes about
  when the gate passes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a coverage shortfall names itself in the behavior gate's result.

## Impact

- `src/ethos/adapters/gates/python_quality.py`, the measurement owner
  `src/ethos/repository/policy/quality_reports.py` and the pytest report owner
  `src/ethos/repository/policy/quality/pytest.py`, with their tests.
