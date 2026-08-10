## MODIFIED Requirements

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
