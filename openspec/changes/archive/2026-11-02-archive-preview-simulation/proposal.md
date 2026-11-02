# Proposal

## Why

`ethos lane archive-change` previews readiness from the Change's lifecycle and commitment, and only
the proof simulates the archive and validates the merged specs strictly
(`archive_readiness_gaps`). A preview can therefore report `ready_to_archive` for a Change whose
merged requirement exceeds OpenSpec's 500-character limit: on 11-01 the apply then failed and
compensated itself, and on 11-02 a full proof refused the same condition one minute after its
start (`openspec_archived_requirement_invalid`).

## What Changes

- The preview of `ethos lane archive-change` runs the archive readiness check that the proof runs
  and blocks with its gaps before any archive effect.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: the archive preview simulates the archive and validates the merged specs.

## Impact

`src/ethos/adapters/mutation/lane_lifecycle/archive/command.py` and its tests.
