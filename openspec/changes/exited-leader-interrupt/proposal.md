# Proposal

## Why

When a command scope is cleaned up, ETHOS interrupts each owned command whose leader still runs, then closes the command's process group.

- The interrupt pass checks the leader with `poll()` and then signals its group. If the leader exits between those two steps, Darwin refuses the group signal with `EPERM`, because the group's members have exited and await their reaper.
- The close pass already tolerates that refusal within a bound (`07913c71b`). The interrupt pass did not: it recorded the refusal as a failure at once. Cleanup then raised `command_scope_cleanup_failed`, which replaced the command's own failure.

A full proof on 2026-10-26 failed this way. The provenance gate's expected refusal (`source_upstream_archive_unqualified`) surfaced as that exception group and broke `test_public_quality_gate_requires_native_artifact_integrity[upstream-drift]`, although the same head had passed it in an earlier proof. Any Darwin proof can hit the race, for ETHOS and for its adopters, so the fix ships in 0.2.0-alpha.16.

## What Changes

- In the interrupt pass, a refusal to signal a group whose leader has exited by the time it is re-checked is left to the close pass. That pass waits, within its bound, until the group is absent.
- A refusal while the leader still runs remains a cleanup failure, as before.
- A changelog entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. The requirement "Interrupted commands retain effect and process ownership boundaries" already requires the original failure to remain observable; this restores it on Darwin.

## Impact

- Code: `src/ethos/adapters/process.py` and `tests/unit/adapters/test_process.py`.
- Linux and Windows behavior does not change. A lasting refusal or a signalable member still fails cleanup.
