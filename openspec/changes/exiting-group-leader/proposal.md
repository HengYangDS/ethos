# Proposal

## Why

On 2026-11-07 at 17:43 the full proof `mlp1` failed in
`test_command_failure_closes_owned_descendants[False-False-cancel-True]`: cancelling a command,
the process owner sent `SIGKILL` to the owned group and Darwin refused with `EPERM` while
`process.poll()` still reported the leader as running. Under load the leader was exiting but not yet
reapable, a window that the owner's existing Darwin rule, written for groups whose members exited
and await their reaper, does not cover, so cleanup failed as if a survivor held the group. The
defect register names it row 26, "cancellation refused while the group leader exits", and the
committee's R11 asks for its diagnosis before the release candidate. Two test bounds of the same
class also failed proofs under load: a loose Git object chosen by set order in `test_gate_policy`
and a 90-second `uv build` bound in the sdist rebuild test.

## What Changes

- A permission refusal while the group leader still reports running waits, within the existing
  reaping grace, for the leader to become reapable, then takes the existing path for an exited
  group. A refusal that outlasts the grace still fails cleanup as a survivor.
- `test_gate_policy` damages a blob chosen deterministically and reports the object store's state
  if the blob is not loose; the sdist rebuild test bounds its `uv build` by 300 seconds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: an exiting group leader is not a survivor.

## Impact

- `src/ethos/adapters/process.py`, `tests/unit/adapters/test_process.py` and the new
  `tests/unit/adapters/test_process_group_refusals.py`.
- `tests/unit/repository/policy/test_gate_policy.py` and
  `tests/unit/release/test_version_identity.py`.
