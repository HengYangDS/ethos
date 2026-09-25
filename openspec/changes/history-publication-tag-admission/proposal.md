## Why

An attested identity repair can replace an entire accepted history while a peer
still holds an earlier commit from that history. Publication currently treats
those verified replacement commits as new work and blocks the exact peer ref.
Separately, native pre-push accepts a plain commit OID as a release tag because
it checks only the peeled commit, not the tag object.

## What Changes

- Admit a protected peer ref at any original commit explicitly mapped by a
  completed history-repair effect for that ref. Validate only commits after the
  verified replacement tip; retain current proof, accepted effect, candidate
  equality and exact peer compare-and-swap.
- Make readiness and native pre-push use the same repaired-history relation.
  Missing, ambiguous, unrelated or tampered evidence remains blocking.
- Require pre-push to inspect the actual signed annotated tag object, its name,
  committed version and accepted source before permitting a release-tag update.
- Add real-Git positive and negative regressions for both boundaries.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: extend verified history-repair publication to an
  attested peer-history prefix and enforce native tag-object admission.

## Impact

The existing history-repair observation, commit-range admission, remote
publication transition, pre-push admission and their native tests. The
repository-governance contract is the semantic owner; no new authority store,
remote protocol, dependency, or adopter-specific bypass is introduced.
