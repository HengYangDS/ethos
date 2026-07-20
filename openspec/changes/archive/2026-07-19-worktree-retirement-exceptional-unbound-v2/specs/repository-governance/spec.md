## ADDED Requirements

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

ETHOS SHALL expose a native exceptional route through `ethos lane retire
unbound` for one unbound `work/*` ref only when the current ref is an ancestor
of the accepted branch, has no linked worktree or active lease, carries an
accepted-Chronicle-bound active Claim, and matches the supplied expected head.
The route SHALL require an
accepted, repository-local Chronicle that contains
`lane_retire/unbound_exceptional`, `target_branch: <branch>`,
`target_head: <head>`, and `target_claim: <claim-id>` for the same exact target.
The named local Claim SHALL be byte-identical to its accepted branch version.
Apply SHALL additionally
require explicit authorization, break-glass, and irreversible confirmation.
The route SHALL NOT infer authority from an agent vendor, session, account, or
host-specific path.

#### Scenario: Exact accepted-ancestor residue is inspected

- **WHEN** an operator supplies an unbound `work/*` ref that is an accepted
  ancestor, has no linked worktree or active lease, and supplies a matching
  accepted Chronicle and Claim, expected head, and reason
- **THEN** dry-run reports `ready_to_retire_unbound_exceptional`
- **AND** it reports the exact observation without deleting the ref
- **AND** it reports that its output does not mint reusable authority.

#### Scenario: A non-exact or non-accepted target is refused

- **WHEN** the target is linked, leased, not an accepted ancestor, lacks a
  Chronicle-bound active Claim, has a mismatched expected head, or its Chronicle
  or Claim is missing, unaccepted, generic, stale, or names another target
- **THEN** ETHOS SHALL block the request before any ref mutation
- **AND** it SHALL leave the target ref and any lease intact.

#### Scenario: Exceptional controls are incomplete

- **WHEN** apply omits authorization, break-glass, or irreversible confirmation
- **THEN** ETHOS SHALL block the request before any ref mutation
- **AND** it SHALL report the missing machine-readable control gaps.

### Requirement: Exceptional unbound effects are compare-and-delete and receipt-bound

For an admitted exceptional unbound retirement, ETHOS SHALL reobserve the exact
target, accepted policy binding, lease state, and protected refs immediately
before effect. It SHALL create a no-clobber local attempt record before calling
`git update-ref -d refs/heads/<branch> <expected-head>`. It SHALL reobserve the
target and protected refs afterwards, require the target ref and unbound reader
entry to be absent and protected refs unchanged, then create a no-clobber local
receipt. It SHALL NOT force-remove a worktree, delete a lease, mutate a remote,
or fall back to unconstrained branch deletion.

#### Scenario: Apply deletes only the observed ref

- **WHEN** all exceptional conditions remain stable through the pre-effect
  reobservation and the compare-and-delete succeeds
- **THEN** ETHOS SHALL report `retired_unbound_exceptional`
- **AND** its receipt SHALL bind the before and after observations, accepted
  Chronicle digest, effect, and postconditions
- **AND** the target ref, unbound reader entry, and active lease SHALL be absent
  while protected refs remain unchanged.

#### Scenario: Observation or postcondition drifts

- **WHEN** the target, accepted Chronicle, protected refs, lease state, record
  publication, or post-effect observation differs from the admitted facts
- **THEN** ETHOS SHALL report a blocked local residue with exact gaps
- **AND** it SHALL not delete a newer ref, remove an active lease, or claim the
  retirement completed.
