# Proposal

## Why

`test-timeout-deadlines` replaced three per-test timeout literals with `seconds("tool")`, and its
proof on 2026-11-08 failed on `tests/architecture/test_hang_bound.py`, the owner of per-test
timeouts: a mark must be a literal below the shared hang bound, and an expression reads as
unbounded. The real defect was narrower: a mark tighter than the tool deadline also timed the test's
setup, so a fixture's `git add` on a busy host ended it.

## What Changes

- `test_source_alias_expansion_is_bounded` builds its repository in a fixture and keeps its
  two-second mark with `func_only=True`, so the mark times only the alias resolution.
- The two native-run tests take the literal mark 60, the tool deadline.
- The hang bound owner also refuses a mark below the tool deadline without `func_only=True`, and the
  separate guard that `test-timeout-deadlines` added retires.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

`tests/unit/adapters/gates/test_markdown_links.py`, `tests/unit/adapters/test_process.py`,
`tests/unit/adapters/process/test_capture.py`, `tests/architecture/test_hang_bound.py` and
`tests/architecture/test_pytest_configuration.py`.
