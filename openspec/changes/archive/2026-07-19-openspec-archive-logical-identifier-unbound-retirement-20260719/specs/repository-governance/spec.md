## MODIFIED Requirements

### Requirement: Exceptional unbound Work Lane retirement is exact and accepted-policy-bound

ETHOS SHALL expose a native exceptional route through `ethos lane retire
unbound` for one unbound `work/*` ref only when the current ref is an ancestor
of the accepted branch, has no linked worktree, carries an
accepted-Chronicle-bound active Claim, and matches the supplied expected head.
The target SHALL have either no active lease or exactly one active lease whose
holder, ID, epoch, and expected head remain bound to the current invocation for
native relinquishment. The route SHALL require an accepted, repository-local
Chronicle that contains `lane_retire/unbound_exceptional`, `target_branch:
<branch>`, `target_head: <head>`, and `target_claim: <claim-id>` for the same
exact target. The named local Claim SHALL be byte-identical to its accepted
branch version. One accepted evidence carrier SHALL bind one target; it SHALL
NOT permit a batch effect or apply to another inventory item. Apply SHALL additionally
require explicit authorization, break-glass, and irreversible confirmation. The
route SHALL NOT infer authority from an agent vendor, session, account, or
host-specific path.

#### Scenario: Exact accepted-ancestor residue is inspected

- **WHEN** an operator supplies an unbound `work/*` ref that is an accepted
  ancestor, has no linked worktree and no active lease, and supplies a matching
  accepted Chronicle and Claim, expected head, and reason
- **THEN** dry-run reports `ready_to_retire_unbound_exceptional`
- **AND** it reports the exact observation without deleting the ref
- **AND** it reports that its output does not mint reusable authority.

#### Scenario: One carrier does not authorize another target

- **WHEN** an operator supplies a Chronicle or Claim for a different unbound ref
- **THEN** the command SHALL block the mismatched target before mutation
- **AND** the target SHALL require its own expected head, Claim, Chronicle,
  current observation, and receipt.

#### Scenario: A non-exact or non-accepted target is refused

- **WHEN** the target is linked, has a foreign, ambiguous, stale, or
  head-mismatched lease, is not an accepted ancestor, lacks a
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
receipt. It SHALL NOT force-remove a worktree, mutate a remote, or fall back to
unconstrained branch deletion.

#### Scenario: Current holder relinquishes one exact lease generation

- **WHEN** all ordinary exceptional controls have passed and the target has an
  active lease whose holder equals the current `ETHOS_ACTOR`, whose ID and epoch
  are present, and whose expected head equals the target head
- **THEN** ETHOS MAY revoke only that exact generation through the native lease
  CAS after publishing its attempt record
- **AND** the attempt and successful receipt bind the exact lease generation and
  CAS result
- **AND** ETHOS SHALL reobserve all non-lease retirement bindings and require
  no active lease before the compare-and-delete ref effect.

#### Scenario: Lease relinquishment remains fail-closed

- **WHEN** a target lease is absent, foreign, malformed, stale, head-mismatched,
  replaced, or cannot be revoked by the exact CAS
- **THEN** ETHOS SHALL leave the source ref intact and report the observed gap
- **AND** it SHALL not claim retirement or use raw lease or ref deletion.

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

#### Scenario: Target-specific evidence remains vendor-neutral

- **WHEN** a target-specific accepted Claim and Chronicle authorize a later
  exceptional unbound Work Lane retirement
- **THEN** their authority SHALL remain limited to their exact branch and head
- **AND** ETHOS SHALL NOT infer deletion authority from an agent vendor,
  account, session, host path, or another target's evidence carrier.
