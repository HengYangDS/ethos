# Proposal

## Why

GitLab pipeline 14607 failed its `verify` job on `599a1d86e` twice, each time on one test whose
bound a loaded Linux CI guest exceeded, while GitHub passed the same commit; on 2026-11-08 the
proof of `record-retirement-apply` failed on the first of them under a host load of 60 to 77:

- `test_cancellation_reaches_native_nox_pytest_worker` in
  `tests/unit/adapters/process/test_capture.py` waited ten seconds for a nested `nox` and `pytest`
  worker's handshake (`tests/support/subprocesses.py` `ready_descendant`);
- `test_native_workflow_gate_preserves_large_input_and_semantic_rejections` in
  `tests/architecture/ci/test_workflow.py` bounded `shellcheck` on a 5,000-line script to 30
  seconds, the bound GitLab job 66604 already exceeded on 2026-11-07.

Both bounds exist to stop a deadlocked child, not to time a loaded runner.

## What Changes

- Both waits use the declared tool deadline, `seconds("tool")`, as `kill_after_marker` beside the
  handshake already does. A passing run is not slower: each wait returns when the child answers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

`tests/support/subprocesses.py` and `tests/architecture/ci/test_workflow.py` only.
