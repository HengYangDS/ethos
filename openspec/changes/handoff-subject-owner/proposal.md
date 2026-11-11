# Proposal

## Why

`revoke-source-subject` gave the revoke report the import report's subject rule by repeating its
expression, `branch or package.resolve().as_posix()`. The repetition raised
`revoke_cross_host_source`'s decision density from its pinned 22 to 23, which the
`unit-architecture` gate refused in the batch's proof, and it left one rule written twice.

## What Changes

- One helper names a handoff report's subject: the manifest's lane, or the resolved package when the
  manifest names none. The import and revoke reports both call it, and the density returns to its
  pin.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Behavior is unchanged.

## Impact

`src/ethos/adapters/mutation/lane_lifecycle/handoff/transfer.py`.
