## Why

Accepted contributions leave review refs behind because the publication model
only represents projecting a nonzero object. Deleting a proposal needs the same
exact peer CAS and recovery guarantees, with fresh absorption and review facts.

## What Changes

- Extend the existing publication effect to retire an exact proposal ref after
  its selected content enters accepted dev and no associated review is open.
- Reobserve each peer, accepted object and review boundary before effects;
  preserve unknown outcomes and resume without repeating completed deletions.
- Expose retirement through the existing public publication command and hooks,
  preserving signatures, protected refs and independently delayed main release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: admit exact remote proposal retirement and recovery.

## Impact

Publication contracts, admission, remote observations, execution, CLI and their
existing tests. Native Git and Forge clients remain effect and observation
transports. No new persistent workflow, adopter carrier, credentials, remote
protection change, history rewrite or review-closing effect is in scope.
