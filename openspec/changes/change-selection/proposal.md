## Why

An archived Change can share its identifier with a canonical capability. An
untyped official query can then return the specification instead of the Change,
preventing accepted closeout from recovering its already-attested intent.

## What Changes

- Select the official Change namespace explicitly when compiling intent.
- Preserve the existing exact archive-effect fallback and digest checks.
- Verify active, archived and missing Change identities through native OpenSpec
  and the public closeout path without weakening invalid-projection rejection.

## Capabilities

### Modified Capabilities

- `contracts`: subject=change-selection; reuse=extend; change=modify

## Impact

The existing OpenSpec Commitment adapter and its direct regression tests own the
repair. No new dependency, persisted model, naming restriction or adopter carrier
is introduced.

## Out Of Scope

- Changing capability names, historical intent, proof policy or adopter files.
- Replacing native OpenSpec parsing or treating any specification as a Change.

