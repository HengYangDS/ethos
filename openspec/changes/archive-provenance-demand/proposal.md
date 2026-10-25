# Proposal

## Why

Archive resolution verifies whole signature-repair histories for archive commits that the repair
did not affect. This makes normal status and prewrite observations exceed their execution deadline.

## What Changes

- Select repair dependencies from their actual affected Git history before full verification.
- Keep relevant repair verification fresh and shared only within the current observation.
- Guard the distinction between an ancestor and an affected commit with a real Git regression.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This repairs execution of existing archive provenance requirements; `skip_specs: true` applies.

## Impact

The existing archive provenance owner and its tests change. Status and prewrite retain their
original admission contracts. No supply pins, locks, release metadata or active runtime changes.
