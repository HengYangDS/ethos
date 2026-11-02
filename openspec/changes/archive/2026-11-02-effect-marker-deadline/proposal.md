# Proposal

## Why

Three tests kill a real ETHOS child at an effect boundary and wait for that boundary with a literal
deadline: `kill_after_marker` waits 45 seconds by default, the signature repair helper 15 and the
release test 30. Each child imports ETHOS and runs a full repair, archive merge or release before it
reaches its marker. On 11-02 the full proof of `828e6ca12` failed
`test_killed_history_repair_recovers_without_repeating_completed_effects[ref-cas]` because its
child reached no marker within 15 seconds while the host's load average was between 17 and 30; the
same test passed three times in a row at a load average of about 14, each case taking 15 to 20
seconds.

## What Changes

- `kill_after_marker` waits for the child's marker within the declared tool deadline,
  `timeout.tool_seconds` (60 seconds by default), and its callers pass no deadline of their own.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Only test helpers change and no requirement names their deadlines, so `skip_specs: true`
applies.

## Impact

`tests/support/subprocesses.py`, `tests/support/signature.py` and
`tests/unit/cli/land/test_release.py`. No product, lock or adopter change.
