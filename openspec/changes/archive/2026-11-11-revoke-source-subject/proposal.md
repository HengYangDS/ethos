# Proposal

## Why

`ethos lane handoff revoke-source` with a package whose manifest is missing raised a validation
error instead of reporting the package's gap. The manifest named no lane, so the report built its
admission subject from an empty resource, which the subject model refuses; the CLI then showed the
model's message as the gap and the manifest's own `handoff_manifest_missing` was lost. `lane handoff
import` already names the package as its subject in that case.

## What Changes

- `revoke-source` names the package as its subject when the manifest names no lane, as `import`
  does, so a missing or unsafe manifest reports its own gap and the command blocks with it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The command already blocks; it now blocks with the manifest's gap instead of a validation
message.

## Impact

`src/ethos/adapters/mutation/lane_lifecycle/handoff/transfer.py`,
`tests/unit/lanes/handoff/test_cross_host_handoff.py` and `CHANGELOG.md`.
