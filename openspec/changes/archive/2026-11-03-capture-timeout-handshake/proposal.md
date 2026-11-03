# Proposal

## Why

GitLab pipeline 14011, the `dev` push of `a584c7543`, failed only in
`test_bulk_stdout_preserves_native_output_and_closes_capture[timeout-False]`: after its 1-second
timeout the captured stdout was empty instead of the 1,245,184-byte payload. The test's child
starts Python, writes its output and then sleeps, while `run_command` starts the timeout as soon as
it waits for the child. On a starved runner the child had not written yet, and an empty capture was
then the correct result. The proposal pipeline of the same commit passed the test.
`test_bulk_stdout_timeout_retains_closed_stderr` races the same way.

## What Changes

- Both timeout tests start the adapter's timeout only after the child has written its output: the
  child then completes the readiness handshake of `ready_descendant` and blocks until the timeout
  ends it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The process adapter does not change.

## Impact

`tests/unit/adapters/process/test_capture.py` only.
