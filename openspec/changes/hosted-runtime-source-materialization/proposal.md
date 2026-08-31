## Why

The archived host-conformance repair reached Hosted execution but exposed two
authority defects. Package-only runtime materialization resolves the Windows
Node executable differently from the delivery pipeline, and a read-only Hosted
source proof attempts to activate repository-local hooks and an accepted
runtime before proving the proposal checkout. Both make valid proposal evidence
depend on the wrong execution owner.

## What Changes

- Make one product-owned resolver define the `nodejs-wheel` Node and npm
  coordinates for both runtime materialization and delivery tooling, including
  the Windows package layout.
- Delete the duplicate CI-only Node resolver after moving its consumers to the
  product owner.
- Make Hosted repository proof configure only the Git identity needed by tests
  and execute source proof directly from the locked checkout environment.
- Remove hook/runtime activation from the read-only Hosted proof path; local
  mutation admission continues to use the immutable selected runtime and hooks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: runtime materialization and delivery resolve the same
  platform-correct Node/npm package coordinates.
- `proof-hosts`: Hosted proposal proof remains a source-proof plane and does not
  mutate Git-common hook/runtime state before proof.

## Impact

The change is limited to the existing runtime input resolver, its delivery
consumers, Hosted proof projections, and focused architecture/unit tests. It
adds no fallback executable lookup, compatibility helper, provider-specific
state, or second proof path.
