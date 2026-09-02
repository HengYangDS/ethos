## ADDED Requirements

### Requirement: Linked Work Lane retirement has one exact effect

ETHOS SHALL route landed and superseded linked Work Lane retirement through one
strict request and semantic owner. It SHALL bind the actor, retirement mode,
target lane ref and HEAD, linked checkout path and cleanliness, and accepted ref
and HEAD as exact operation facts. When the operation consumes a Lease, it SHALL
bind only the Lease's lane ref, holder ref, generation, and expiry under the
SQLite transaction; Git coordinates SHALL remain independently observed facts.
It SHALL remove only the selected clean checkout and compare-and-delete only the
exact lane ref in a Git transaction that also verifies the accepted ref.

Landed retirement of a lane already contained in accepted truth SHALL be a
Commitment-free deletion-only repository effect and SHALL accept an exact valid,
expired, or missing Lease observation under the corresponding effect-time
recheck. Superseded retirement SHALL retain its selected proof, transient
Commitment, absorption authority, and valid Lease requirements. If a prior
failed superseded retirement preserved the exact Work Lane ref and valid Lease
but left its worktree absent, it MAY use the one existing partial-recovery path.
That path SHALL revalidate the ref, HEAD, tree, selected proof and Commitment,
four-field Lease generation, actor, path absence, worktree registration, and
absorption authority before recreating the exact branch-bound worktree. A
blocked later effect SHALL preserve the recovered worktree or report its exact
compensation failure.

#### Scenario: Exact Lease observation changed after planning

- **WHEN** a planned live or expired Lease differs in lane ref, holder ref,
  generation, or expiry at effect time
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current Lease intact.

#### Scenario: A Lease appears after an absent observation

- **WHEN** landed retirement planned against an absent Lease and a row for the
  target lane exists when the SQLite transaction re-observes it
- **THEN** ETHOS blocks the effect
- **AND** it does not delete the linked worktree, branch, or new Lease.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite Lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS re-observes the ref, worktree, and Lease postconditions
- **AND** it reports the exact non-terminal state without claiming retirement.

#### Scenario: Landed and superseded commands share one owner

- **WHEN** a caller invokes ordinary landed or superseded linked retirement
- **THEN** both CLI commands construct the same strict request model and call
  the same linked-retirement effect
- **AND** the plan records the selected retirement mode so landed cleanup cannot
  consume superseded proof authority and superseded retirement cannot silently
  weaken to deletion-only admission
- **AND** no wrapper, re-export, compatibility summary, or parallel Python
  effect remains.

#### Scenario: Exact partial superseded retirement recovers and retires

- **GIVEN** a `work/*` ref remains at the planned Git HEAD and tree
- **AND** its valid Lease is held by the invoking actor
- **AND** the prior linked path is absent and not registered or reused
- **AND** accepted truth exactly absorbs the lane semantics
- **WHEN** the owner supplies that path to authorized superseded retirement
- **THEN** dry-run reports recovery and retirement readiness without mutation
- **AND** apply recreates the exact linked worktree and resumes the existing
  linked retirement effect
- **AND** terminal success requires the Lease, ref, and worktree all absent.

#### Scenario: Partial recovery coordinates drift

- **WHEN** the path collides, the ref moves, the Lease or tree changes, the
  Commitment cannot be verified, or the actor is not the current holder
- **THEN** ETHOS blocks before recreating a worktree
- **AND** it preserves the current ref and Lease unchanged.

#### Scenario: Retirement blocks after recovery

- **WHEN** exact worktree recovery succeeds but the subsequent ref transaction
  or Lease closeout blocks
- **THEN** ETHOS leaves the exact recovered linked worktree available for the
  normal public retry path
- **AND** it reports the failing transition and observed native carrier states
  without claiming retirement.

## MODIFIED Requirements

### Requirement: Work Lane Lifecycle Resolution

Routine lifecycle SHALL remain mechanically derived from current facts and exact
plans. A clean linked Work Lane whose exact HEAD equals or is an ancestor of the
current accepted HEAD SHALL be eligible for deletion-only landed retirement
without reconstructing historical proof, Commitment, or Lease authority.
Exceptional interpretive judgment SHALL remain an exact, non-authorizing
Attestation selected by the operation; Chronicle SHALL have no current reader or
producer.

#### Scenario: routine lifecycle remains local

- **WHEN** coordination is mechanically determined
- **THEN** ETHOS uses local Lease fencing when a live Lease exists and
  postcondition Attestations for the applied effects
- **AND** no tracked decision record is required

#### Scenario: clean linked accepted residue retires without historical proof

- **WHEN** a named linked `work/*` Lane is clean and its exact HEAD equals or is
  an ancestor of the freshly observed accepted HEAD
- **AND** its ref, worktree binding, accepted ref, actor, and requested HEAD are
  unchanged at effect time
- **THEN** `ethos lane retire landed` SHALL remove only that exact worktree and
  branch through the existing exact-CAS effect owner
- **AND** it SHALL compile the deletion as a repository effect with no
  Commitment or proof-Attestation prerequisite
- **AND** it SHALL emit exact effect and postcondition evidence

#### Scenario: live Lease retains holder authority

- **WHEN** an otherwise retireable linked Lane has a valid Lease
- **THEN** only the exact current holder MAY apply landed retirement
- **AND** the Lease generation SHALL be re-observed and revoked exactly in the
  same bounded transition

#### Scenario: absent or expired Lease does not resurrect history

- **WHEN** an otherwise retireable linked Lane has no Lease or only an expired
  exact Lease row
- **AND** the invocation names a non-empty actor and explicitly authorizes the
  deletion-only transition
- **THEN** ETHOS SHALL respectively require the Lease to remain absent or revoke
  the exact expired row before committing retirement
- **AND** it SHALL NOT require Lease reacquisition, holder impersonation,
  historical proof, or a compatibility carrier

#### Scenario: unsafe retirement remains blocked

- **WHEN** the selected Lane is dirty, its HEAD is not accepted ancestry, its
  Lease state is unknown, a valid Lease belongs to another holder, or any exact
  Git, worktree, Lease, actor, or accepted coordinate drifts
- **THEN** retirement SHALL fail closed without deleting the branch or worktree
- **AND** no inventory entry, stale receipt, self-supplied holder, or historical
  relation SHALL substitute for the missing fact

#### Scenario: exceptional cleanup consumes prior accepted judgment

- **WHEN** an exceptional destructive operation requires human judgment
- **THEN** a separately accepted Commitment and bound decision Attestation name
  exact target, evidence, disposition, recovery, and validity
- **AND** the operation re-observes mutable facts before its first effect

#### Scenario: dirty or unknown work is preserved by default

- **WHEN** ownership, Lease, content, or recovery status is unknown or dirty
- **THEN** ETHOS preserves or blocks rather than inferring authority
- **AND** irreversible deletion requires exact accepted judgment and evidence

#### Scenario: break-glass reconciles after emergency action

- **WHEN** a predeclared break-glass Commitment admits an emergency effect
- **THEN** the result is an exact Attestation and later integration remains
  blocked until accepted reconciliation
- **AND** a self-supplied flag or holder string is insufficient

#### Scenario: lane handoff is recorded as Chronicle resolution

- **WHEN** an exceptional handoff judgment is required
- **THEN** it is recorded as a decision Attestation, not Chronicle
- **AND** it does not replace the destination-local Lease

#### Scenario: orphan audit produces a decision, not a persistent orphan state

- **WHEN** a lane has missing or ambiguous holder evidence
- **THEN** orphan-like facts remain observations and accepted disposition is an
  Attestation
- **AND** no persistent orphan or Chronicle state is created

#### Scenario: clean ownerless diverged source retires after semantic absorption

- **WHEN** exact accepted judgment and evidence admit retirement
- **THEN** the resolver re-observes the source and emits an effect Attestation
- **AND** the authority does not extend to another lane or remote effect

### Requirement: Lease generation identity is complete across boundaries

ETHOS SHALL represent one exact Lease generation with exactly its lane ref,
holder ref, positive generation, and expiry across workspace status, handoff
packages, retirement attempts, receipts, and mutation effects. It SHALL reject
incomplete or stale Lease bindings and SHALL NOT persist a parallel identifier,
fingerprint, Git coordinate, Commitment identity, workflow field, or effect
outcome in the Lease. Git HEAD and tree, package identity, and effect evidence
SHALL remain independently bound by their native facts, content identities, and
Attestations.

#### Scenario: A boundary omits or changes a Lease fact

- **WHEN** an otherwise matching Lease binding omits or changes lane ref, holder
  ref, generation, or expiry
- **THEN** ETHOS rejects the handoff, retirement, or mutation effect
- **AND** the current Lease and Git carriers remain unchanged.

#### Scenario: Unavailable-holder recovery is admitted

- **WHEN** accepted policy admits unavailable-holder retirement for one complete
  foreign Lease generation
- **THEN** ETHOS calls the same exact revoke primitive used by ordinary holder
  relinquishment
- **AND** no unavailable-holder wrapper or parallel destructive effect exists.

#### Scenario: Cross-host destination import is acknowledged

- **WHEN** the package target actor imports one verified handoff package
- **THEN** ETHOS creates one destination-local Lease generation
- **AND** its content-addressed acknowledgement binds the package identity and
  exact source Git facts separately from the destination lane ref, holder ref,
  generation, and expiry
- **AND** edited, incomplete, or non-target acknowledgements cannot authorize
  source revocation.

#### Scenario: Cross-host import fails after Lease acquisition

- **WHEN** destination restoration fails after the new Lease is acquired
- **THEN** ETHOS removes only the exact created Git carriers
- **AND** revokes only that exact Lease generation after carrier absence is
  proven
- **AND** uncertain compensation retains observable state and fails closed.

#### Scenario: The same content-addressed package is exported again

- **WHEN** the derived package directory already exists
- **THEN** ETHOS verifies and reuses the identical immutable package
- **AND** it never recursively deletes or replaces existing package content.

## REMOVED Requirements

### Requirement: Linked Work Lane retirement has one generation-bound effect

ETHOS SHALL route landed and superseded linked Work Lane retirement through one
strict request and semantic owner. Under a SQLite generation lock it SHALL bind
the actor, complete lease generation and payload identity, lane ref, and
expected head; then recheck the accepted control root and head, lane relation,
linked checkout head, and cleanliness. It SHALL remove only that clean checkout
and compare-and-delete only the exact lane ref in a Git transaction that also
verifies the accepted ref. If a prior failed retirement preserved the exact
Work Lane ref and valid Lease but left its worktree absent, superseded
retirement MAY accept one explicit recovery path. It SHALL revalidate the exact
ref, HEAD, tree, Commitment, Lease generation, holder, actor, path absence,
worktree registration, and absorption authority before recreating that one
branch-bound worktree through the native worktree effect. It SHALL then resume
the same linked retirement transaction. A blocked later effect SHALL preserve
the recovered linked worktree or report its exact compensation failure.

#### Scenario: Exact lease generation changed after planning

- **WHEN** the lease ID, holder, epoch, lane ref, expected head, row expiry, or
  raw payload digest no longer matches the planned linked retirement
- **THEN** ETHOS blocks the effect
- **AND** it leaves the linked worktree, lane ref, and current lease intact.

#### Scenario: Accepted ref changes during linked retirement

- **WHEN** the accepted ref differs after the worktree is removed but before the
  lane ref transaction commits
- **THEN** the Git ref transaction rejects lane-ref deletion
- **AND** the SQLite lease deletion rolls back
- **AND** ETHOS reports a blocked partial transition without claiming retirement.

#### Scenario: Lease commit fails after Git removal

- **WHEN** the clean worktree and exact lane ref were removed but the SQLite
  transaction cannot commit
- **THEN** ETHOS rolls back the lease deletion
- **AND** it restores the exact lane ref only if that ref remains absent
- **AND** it reports whether the no-clobber compensation succeeded.

#### Scenario: Landed and superseded commands share one owner

- **WHEN** a caller invokes ordinary landed or superseded linked retirement
- **THEN** both CLI commands construct the same strict request model and call
  the same linked-retirement effect
- **AND** no wrapper, re-export, compatibility summary, or parallel Python
  effect remains.

#### Scenario: exact partial retirement state recovers and retires

- **GIVEN** a `work/*` ref remains at the Lease-bound expected HEAD and tree
- **AND** its valid Lease is held by the invoking actor
- **AND** the prior linked path is absent and not registered or reused
- **AND** accepted truth exactly absorbs the lane semantics
- **WHEN** the owner supplies that path to authorized superseded retirement
- **THEN** dry-run reports recovery and retirement readiness without mutation
- **AND** apply recreates the exact linked worktree and resumes the existing
  linked retirement effect
- **AND** terminal success requires the Lease, ref, and worktree all absent.

#### Scenario: partial recovery coordinates drift

- **WHEN** the path collides, the ref moves, the Lease or tree changes, the
  Commitment cannot be verified, or the actor is not the current holder
- **THEN** ETHOS blocks before recreating a worktree
- **AND** it preserves the current ref and Lease unchanged.

#### Scenario: retirement blocks after recovery

- **WHEN** exact worktree recovery succeeds but the subsequent ref transaction
  or Lease closeout blocks
- **THEN** ETHOS leaves the exact recovered linked worktree available for the
  normal public retry path
- **AND** it reports the failing transition and observed native carrier states
  without claiming retirement.
