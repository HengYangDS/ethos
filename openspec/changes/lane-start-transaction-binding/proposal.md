## Why

Fresh Work Lane creation can pass dry-run and begin Git/worktree effects before
it discovers that the repository Commitment is present but invalid or obsolete.
The apply path then misreports the carrier as missing and may claim compensation
failure even when no residue exists.

## What Changes

- Classify repository Commitment observation precisely as absent, unreadable,
  unsupported schema, semantically invalid, or identity-mismatched.
- Make lane-start dry-run and apply consume the same repository-bound,
  prevalidated Commitment and repository identity before any ref, worktree,
  Lease, or carrier effect.
- Preserve the original failure through plan, proof, publication, and lane
  consumers rather than translating every validation failure to missing.
- Make zero-effect failures report the observed final state without invented
  cleanup or compensation gaps.
- Delete the broad exception translation and any downstream missing-only
  assumptions replaced by the shared observation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: repository Commitment selection and fresh Work Lane
  creation fail early with one precise carrier state and truthful zero-effect
  receipts.

## Impact

The bounded change modifies the existing repository Commitment reader, fresh
Work Lane transaction preflight, and focused producer-to-consumer tests.
Forward migration of obsolete Commitment carriers remains a separate public
operation; this change adds no legacy reader, fallback, second carrier, or
adopter-specific exception.
