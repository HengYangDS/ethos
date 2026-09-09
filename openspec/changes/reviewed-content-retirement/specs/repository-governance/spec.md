## ADDED Requirements

### Requirement: Reviewed content retirement binds the exact destructive preimage

ETHOS SHALL allow an explicitly reviewed historical topic to retire through its
existing receipt-bound abandonment and recovery capability. The selected
content, index, root identity, ref, accepted object, actor and Lease coordinates
SHALL remain exact effect inputs. Ignored status SHALL NOT imply disposal
permission, and the receipt SHALL NOT claim semantic acceptance from hashes.

Destructive application SHALL operate after all actual writers have stopped
and participants honor lane coordination through disposal. The operator SHALL
verify that handoff before reviewing content. Lease transfer and an empty
process scan SHALL NOT be treated as stopping writers or excluding arbitrary
uncooperative same-UID writes. Unknown liveness SHALL block application.

#### Scenario: Actual writer is stopped before reviewed retirement
- **WHEN** a writer still consumes the selected worktree
- **THEN** retirement rejects application and preserves its content and refs
- **AND** after the writer exits, the operator reviews the final exact content
  under current coordination before applying retirement
- **AND** successful application and recovery remove only the reviewed resources.

#### Scenario: Reviewed absorbed lane has residual content
- **WHEN** an operator derives and reviews an exact receipt for a non-protected
  historical topic whose remaining content has been absorbed, superseded or
  explicitly rejected with a reason
- **THEN** explicit authorized application removes only that selected worktree,
  ref and Lease through the existing operation
- **AND** no backup lane, archive directory or parallel lifecycle is created.

#### Scenario: Content or authority changes after review
- **WHEN** the selected filesystem, index, ref, accepted object, actor or Lease
  no longer matches the receipt, or its observation is unsafe or unavailable
- **THEN** retirement stops before the next destructive effect
- **AND** unresolved bytes and current resources remain protected.

#### Scenario: Historical coordination has expired or disappeared
- **WHEN** a reviewed non-protected topic has missing or expired coordination,
  including a historical commit predating the repository adoption profile
- **THEN** an identified operator can derive and authorize exact deletion from
  the current accepted control checkout without recreating a Lease or profile
- **AND** a valid foreign holder or a Lease acquired after derivation blocks
  the old operation before further deletion
- **AND** expired coordination grants neither ordinary ref updates nor deletion
  of additional or unrelated refs.

#### Scenario: Ignored and read-only generated resources are selected
- **WHEN** an exact reviewed inventory includes ignored or read-only resources
  in an owned isolated root with no active consumers
- **THEN** their safe removal is part of that same bounded retirement
- **AND** external link targets and shared file permissions remain unchanged.

#### Scenario: Native node ownership or filesystem boundary is foreign
- **WHEN** a selected root, descendant or index node has a different native
  owner, or its device differs from the containing directory
- **THEN** derivation rejects the node before opening its content or traversing
  it and does not persist a disposal request
- **AND** effect-time observation applies the same admission boundary.

#### Scenario: An admitted retirement is interrupted
- **WHEN** retirement has partially completed and the operator invokes recovery
  with the original exact receipt
- **THEN** current observations select only remaining admitted effects
- **AND** already completed effects are not replayed and new content is not
  deleted under an obsolete receipt.

#### Scenario: Another retirement holds repository coordination
- **WHEN** application or recovery encounters an already-held retirement lock
- **THEN** it promptly returns `lane_retirement_in_progress`, the exact request
  receipt identity and the existing receipt-bound recovery command
- **AND** it makes no content, ref or Lease effects and claims no unobserved
  progress
- **AND** after normal holder exit or process death, recovery reacquires the
  lock and revalidates current facts rather than replaying assumed effects.

#### Scenario: Ref transaction advances during stale-intent reclamation
- **WHEN** reclamation observes an expired issued ref intent but its record is
  renewed or advances to prepared or committed before the existing lock is held
- **THEN** reclamation preserves the current record and reports that it changed
- **AND** unchanged expired issued records remain reclaimable; matching identity
  alone never authorizes deletion of a changed transaction state.

#### Scenario: Ref intent writer exits while holding coordination
- **WHEN** a live writer holds intent coordination, including during cleanup
- **THEN** competing mutations return a bounded timeout and preserve its record
- **AND** normal exit or process death permits a fresh exact claim without
  deleting a live holder's lock or discarding the transaction
- **AND** coordination-file count does not grow with transaction history
- **AND** unavailable native locking prevents mutation rather than silently
  substituting an existence-marker protocol.
