# Proposal

## Why

`hook install` retires shared host-store installations that no recorded consumer still needs. Its
liveness check treats a consumer path that no longer exists as released
(`src/ethos/adapters/repo/runtime/materialization/host_retention.py:84-85`), so a repository on an
unmounted volume, or one moved without telling ETHOS, loses its pinned runtime the next time
another repository runs `hook install`. The distribution specification forbids this: "Unknown
liveness SHALL prevent deletion" (requirement `Installed product migration preserves live
consumers`). beta.6 listed the defect as known and unowned (`CHANGELOG.md`, known open defects),
and the 2026-11-07 expert committee made its fix RC-blocking (resolution R7(a),
`build/runtime/work/committee-20261107/resolution-r3.md`).

## What Changes

- A consumer whose path does not exist is unknown liveness. Its record stays, and so does every
  installation it recorded.
- The retention report lists those absent consumers, so the operator sees why an installation
  stays.
- Releasing an absent consumer stays a separate, explicit and previewed step. It lands with the
  store-retention Change (resolution R7(c)), before the RC, so retention can still converge.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The fix enforces an existing requirement, so `skip_specs: true` applies.

## Impact

- `src/ethos/adapters/repo/runtime/materialization/host_retention.py` and
  `tests/unit/adapters/repo/runtime/materialization/test_host_retention.py`.
- Behavior: an installation that only a removed repository recorded is no longer retired
  automatically; it stays until its consumer is released explicitly.
