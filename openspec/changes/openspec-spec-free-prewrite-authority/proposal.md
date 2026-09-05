## Why

A valid `skip_specs: true` Change cannot currently authorize its own
implementation: ETHOS waits for every task checkbox to be complete before it
compiles a Commitment, while tracked product writes require that Commitment.
This also makes task progress part of acceptance identity even though progress
is not Commitment semantics.

## What Changes

- Compile deterministic spec-free acceptance as soon as the official metadata,
  proposal, design, and tasks artifact graph is complete, without requiring
  implementation tasks to be marked done.
- Canonicalize the tasks artifact for Commitment identity so checkbox progress
  changes do not alter acceptance while task descriptions remain bound.
- Preserve fail-closed behavior for missing, malformed, non-spec-free, or
  incomplete official artifacts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Separate official spec-free intent completeness from
  task execution progress so an owned Work Lane can obtain bounded prewrite
  authority before implementation.

## Impact

The change affects only official OpenSpec Commitment compilation and its focused
admission/compiler tests. It removes a circular authority dependency without
adding a carrier, compatibility path, or persistent workflow state.
