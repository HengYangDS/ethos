## ADDED Requirements

### Requirement: Ownerless closeout admission is consumed at the effect boundary

ETHOS SHALL retire a clean linked ownerless Work Lane only when the effect
executor validates every admission binding returned by the retired external
verifier, atomically fences the exact
target against lease acquisition, re-observes the admitted target after the
fence is held, and executes an accepted-ref-bound exact deletion CAS without a
force flag. It SHALL issue a completion receipt only after all native
postconditions are verified.

#### Scenario: exact ownerless target is retired

- **GIVEN** an accepted clean ownerless work/* lane and immutable resolution
  decision name the same branch, head, path, Chronicle, and observation
- **AND** the retired external verifier returns the same executor, accepted
  head, decision digest,
  coordination binding, accepted-ancestor relation, and clear occupancy
- **WHEN** ETHOS atomically acquires the exact target fence and all bindings
  remain unchanged
- **THEN** ETHOS SHALL prepare accepted-ref verification plus exact target-ref
  deletion, remove the registered worktree without force, and commit
- **AND** it SHALL verify explicit ref absence, worktree registration absence,
  path absence, accepted head, coordination, decision, and fence postconditions
  before writing a fully bound receipt.

#### Scenario: decision snapshot replacement is rejected

- **GIVEN** effect or completed-effect recovery already admitted decision
  payload A
- **WHEN** the decision path contains a different valid payload B before the
  retired external verifier,
  fence acquisition, or recovery postcondition verification
- **THEN** ETHOS SHALL reject the effect before Git, worktree, fence, or
  reservation mutation
- **AND** every later binding SHALL derive from one strictly parsed decision
  snapshot.

#### Scenario: late coordination or competing decision blocks zero-effect

- **GIVEN** the retired external verifier returned an ownerless admission
- **WHEN** a lease, Claim, accepted-head drift, decision drift, path drift, or
  another target reservation wins before ETHOS acquires or consumes the fence
- **THEN** ETHOS SHALL perform no Git or worktree effect
- **AND** it SHALL report the exact blocking binding without minting ownership.

#### Scenario: worktree-remove failure is re-observed

- **GIVEN** the ref transaction is prepared for one exact target
- **WHEN** git worktree remove returns non-zero
- **THEN** ETHOS SHALL re-read the target ref, worktree registration, and path
- **AND** it SHALL retain reserved_no_effect only when all three remain
  unchanged
- **AND** it SHALL otherwise record worktree_removed_ref_present or
  transition_unknown for explicit reconciliation.

#### Scenario: target-ref inspection is three state

- **GIVEN** ownerless effect postconditions are being verified
- **WHEN** the exact target ref is present, explicitly absent, or cannot be
  inspected
- **THEN** only explicit absence SHALL satisfy the postcondition
- **AND** an inspection error or exception SHALL fail closed rather than being
  treated as absence.

#### Scenario: destructive partial transition remains visible and recoverable

- **GIVEN** the target fence and visible ownerless target reservation exist for
  one exact decision
- **WHEN** worktree removal, ref commit, postcondition verification, receipt
  persistence, or cleanup becomes partial or uncertain
- **THEN** inventory SHALL expose the target, decision, phase, and observed
  recovery state
- **AND** ETHOS SHALL retain visible evidence until the same decision safely
  completes or a separate explicit reconciliation transition resolves it.

#### Scenario: receipt-present cleanup retry converges

- **GIVEN** the exact immutable completion receipt is durable and cleanup is
  incomplete after a crash, whether the visible ownerless reservation remains
  or its unlink already completed
- **WHEN** the same decision retries
- **THEN** ETHOS SHALL validate the receipt schema and exact
  decision/lane/head/ownerless binding, re-verify effect postconditions, and
  perform only idempotent cleanup
- **AND** it SHALL NOT rerun the retired external verifier, repeat a
  Git/worktree effect, recreate effect
  authority, or rewrite the immutable receipt
- **AND** a mismatched receipt, different fence, or unverifiable fence state
  SHALL block.

#### Scenario: closeout-fence inspection is three state

- **GIVEN** pre-effect or receipt-present recovery inspects the exact target fence
- **WHEN** the fence is exactly present, explicitly absent, or cannot be verified
- **THEN** pre-effect SHALL require the exact present fence
- **AND** recovery MAY accept explicit absence only with the exact immutable
  receipt and matching non-fence postconditions
- **AND** an unreadable, malformed, missing-store, or otherwise unverifiable
  fence state SHALL fail closed.

#### Scenario: successful cleanup preserves ordering

- **GIVEN** an exact completion receipt has been persisted
- **WHEN** ETHOS cleans ownerless coordination
- **THEN** it SHALL release the SQLite target fence through exact CAS before
  deleting the visible ownerless target reservation
- **AND** a fence-release failure SHALL retain the visible reservation.

#### Scenario: effect-complete recovery precedes ordinary observation

- **GIVEN** the reservation state is effect_complete_receipt_missing
- **WHEN** the same decision retries
- **THEN** ETHOS SHALL recover or validate the exact completion receipt before
  ordinary lane observation
- **AND** it SHALL NOT depend on observing a worktree already removed by the
  completed effect.

#### Scenario: dangling path and post-CAS exception fail closed

- **GIVEN** ownerless effect or postconditions are being evaluated
- **WHEN** the target path is a dangling symlink or an ordinary exception occurs
  after the CAS boundary
- **THEN** the path SHALL remain present for safety evaluation
- **AND** the exception SHALL become transition_unknown with explicit
  reconciliation required.

#### Scenario: published retired external-verifier coordination shape is exact

- **GIVEN** the retired external verifier returns the currently published
  ownerless coordination object
- **WHEN** a required coordination field is missing, has the wrong type or
  value, or an unpublished field such as lease_id, holder_ref, or lease is
  present
- **THEN** ETHOS SHALL reject the admission with a stable field-specific gap
- **AND** it SHALL NOT infer compatibility with an unversioned future shape.

#### Scenario: canonical and legacy reservations disagree

- **GIVEN** canonical and legacy artifact roots contain valid reservations for
  the same decision
- **WHEN** any validated field differs, including phase, recovery_state, or
  postcondition_digest
- **THEN** inventory SHALL report a blocking record conflict
- **AND** it SHALL NOT select one root as authoritative for effect recovery.

#### Scenario: receipt compatibility is one way

- **GIVEN** historical unversioned completion receipts may remain readable
- **WHEN** ETHOS writes a new completion receipt
- **THEN** the writer SHALL emit schema_version = 2
- **AND** explicit receipt versions other than 2 SHALL be invalid
- **AND** ownerless executor references SHALL satisfy the canonical
  provider-neutral HolderRef wire contract.

#### Scenario: damaged fence payload preserves independent lease truth

- **GIVEN** the lease table and closeout-fence table schemas are current
- **WHEN** one closeout-fence payload cannot be decoded as a JSON object
- **THEN** state inventory SHALL report the closeout-fence projection invalid
- **AND** it SHALL continue to report the independently validated lease schema
  as current.
