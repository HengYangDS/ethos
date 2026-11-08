# Proposal

## Why

The 2026-11-08 proof of `load-tolerant-test-bounds` failed on
`test_source_alias_expansion_is_bounded`, whose `@pytest.mark.timeout(2)` timed the fixture's
`git add` on a loaded host, not the alias cycle the test bounds. The suite has three such per-test
markers with a literal under the declared tool deadline (2, 5 and 30 seconds), and each one ends a
whole test, setup included, on a host that is merely busy.

## What Changes

- The three markers use `seconds("tool")`, the deadline the suite already uses for native tools.
- An architecture test refuses a per-test `pytest.mark.timeout` with a literal below that deadline,
  so the class cannot return one marker at a time.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

`tests/unit/adapters/gates/test_markdown_links.py`, `tests/unit/adapters/test_process.py`,
`tests/unit/adapters/process/test_capture.py` and `tests/architecture/test_pytest_configuration.py`.
