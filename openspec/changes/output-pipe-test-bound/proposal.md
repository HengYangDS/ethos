# Proposal

## Why

Proof b10p5 of 2026-11-13 failed one test of 9,160 under a host load of 85 to 94:
`tests/unit/surface/cli/test_output.py::test_real_full_nonblocking_pipe_preserves_one_failed_exit`
waits 5 seconds for a Python subprocess that imports ETHOS's output module, and the subprocess did
not finish in time. Batch 3 changed nothing it runs; the bound, not the behavior, failed.

## What Changes

- The test waits for its subprocess for the shared tool deadline, `seconds("tool")`, as the other
  subprocess tests do since `load-tolerant-test-bounds`. Its assertions are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Behavior is unchanged, so `skip_specs: true` applies.

## Impact

`tests/unit/surface/cli/test_output.py`.
