## Why

Hook/runtime activation is repository-common, but its post-observation currently
reinterprets the tracked profile from every linked worktree. An old linked
checkout can therefore veto installation of the accepted runtime even though it
is only a projection consumer, not the source-identity authority.

## What Changes

- Observe the expected runtime source identity once from the invoking repository
  authority before activation.
- Use that one identity when validating every linked-worktree projection.
- Keep failure closed when the invoking authority cannot supply an identity.
- Remove per-worktree source interpretation from the activation transaction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: common hook activation has one source-identity
  authority; linked worktrees validate projections only.

## Impact

This narrows the existing installer and its regression coverage. It introduces
no compatibility reader, fallback identity, registry, or second activation
owner.
