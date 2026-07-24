## REMOVED Requirements

### Requirement: Ownerless closeout admission is consumed at the effect boundary

**Reason**: The accepted requirement makes an unrelated external verifier and
mixed predecessor record roots part of current effect authority.

**Migration**: Use the native ownerless closeout authority requirement below.
Predecessor records remain immutable history and no compatibility path is
retained.

## ADDED Requirements

### Requirement: Native ownerless closeout authority is consumed at the effect boundary

ETHOS SHALL retire a clean linked ownerless Work Lane only when its native effect
executor validates the immutable decision and Chronicle, configured Work Lane
role, exact Git worktree registration and incarnation, clean ownerless
coordination state, accepted ancestry, and a complete fence-held re-observation.
It SHALL execute a no-force worktree removal and accepted-ref-bound exact target
deletion CAS, verify all postconditions, and only then issue a provider-neutral
completion receipt. No external verifier, adapter response, predecessor record
root, or compatibility alias SHALL be required for current authority.

#### Scenario: exact ownerless target is retired natively

- **GIVEN** an immutable decision and Chronicle name one clean ownerless Work
  Lane whose branch has the configured Work Lane role
- **AND** Git registration, path, HEAD, incarnation, accepted ancestry, lease,
  Claim, holder, and target digests match the decision
- **WHEN** ETHOS acquires the exact target fence and the complete observation
  remains unchanged
- **THEN** ETHOS SHALL verify the accepted ref, remove the registered worktree
  without force, delete the exact target ref through CAS, and verify explicit
  ref, registration, path, coordination, decision, and fence postconditions
- **AND** it SHALL write the immutable completion receipt only after those
  postconditions pass.

#### Scenario: decision or Chronicle replacement is rejected

- **GIVEN** effect or completed-effect recovery admitted one decision snapshot
  and its bound Chronicle
- **WHEN** either file bytes, digest, disposition, lane identity, or observation
  binding changes before effect or recovery verification
- **THEN** ETHOS SHALL reject the transition before any new Git, worktree,
  fence, reservation, cleanup, or receipt effect.

#### Scenario: configured Work Lane role is authoritative

- **GIVEN** repository policy configures a Work Lane branch prefix other than
  the product default
- **WHEN** an exact registered branch satisfies that configured role
- **THEN** ownerless admission SHALL accept the role without hard-coded branch
  spelling
- **AND** a branch outside the configured role SHALL be rejected.

#### Scenario: late coordination or accepted drift blocks zero effect

- **GIVEN** native preflight observed an ownerless target
- **WHEN** a lease, Claim, holder, accepted-head change, decision change, path
  change, target change, or competing reservation wins before the fence-held
  observation is consumed
- **THEN** ETHOS SHALL perform no Git or worktree effect and SHALL report the
  exact blocking binding without minting ownership.

#### Scenario: accepted ancestry is required

- **GIVEN** the exact target and accepted HEAD are observable
- **WHEN** the target HEAD is not an ancestor of the accepted HEAD or ancestry
  cannot be verified
- **THEN** ETHOS SHALL reject ownerless retirement before effect.

#### Scenario: worktree-remove and ref inspection are three state

- **GIVEN** the exact ref transaction is prepared
- **WHEN** worktree removal, target-ref inspection, or fence inspection reports
  present, absent, or unverifiable state
- **THEN** only the state required by the current phase SHALL pass
- **AND** an error, malformed payload, or exception SHALL remain visible as a
  partial or unknown transition rather than being treated as absence.

#### Scenario: worktree-remove failure is classified by re-observation

- **GIVEN** the exact ref transaction is prepared for one target
- **WHEN** no-force worktree removal returns non-zero
- **THEN** ETHOS SHALL re-read the exact target ref, worktree registration, and
  path
- **AND** it SHALL retain `reserved_no_effect` only when all three remain
  unchanged, classify removed-registration with a present ref as
  `worktree_removed_ref_present`, and classify any other uncertain combination
  as `transition_unknown`.

#### Scenario: zero-effect retry may rebind a descendant accepted head

- **GIVEN** one exact reservation remains `reserved_no_effect`, the same
  decision, executor, target, registration token, and coordination bindings still
  hold, and no Git or worktree effect occurred
- **WHEN** exact pre-fence admission classifies that reservation as the same
  zero-effect retry and the current accepted HEAD equals or descends from the
  reserved accepted HEAD
- **THEN** ETHOS SHALL release the old exact fence and reservation, acquire a
  fresh exact fence, and complete the full under-fence re-observation before
  persisting a new reservation or starting effect
- **AND** divergence, target drift, decision drift, registration drift, or
  unverifiable state SHALL block without effect.

#### Scenario: current record authority is isolated from history

- **GIVEN** predecessor records remain in historical accepted or worktree roots
- **WHEN** ETHOS decides, applies, recovers, writes a receipt, clears, or
  inventories current lane-resolution state
- **THEN** it SHALL access only the versioned current record root
- **AND** history SHALL NOT create a conflict, authorize an effect, or be
  deleted by current cleanup.

#### Scenario: decision-only records are visible

- **GIVEN** a valid current decision exists without a manifest, receipt, clear
  record, or reservation
- **WHEN** current inventory runs
- **THEN** it SHALL include the decision identifier, report
  `state=decision_pending`, and increment decision and pending-decision counts.

#### Scenario: invalid current payload blocks

- **GIVEN** any payload is present in the versioned current record root
- **WHEN** its typed contract, version, canonical bytes, or cross-field
  invariant is invalid
- **THEN** current inventory and effect admission SHALL report a blocking
  integrity gap and SHALL NOT silently ignore the payload.

#### Scenario: current records use explicit provider-neutral versions

- **WHEN** ETHOS writes a new completion receipt, ownerless reservation, or clear
  receipt
- **THEN** it SHALL write receipt schema version 3, reservation schema version
  2, and clear schema version 1
- **AND** the ownerless binding SHALL contain only executor, decision digest,
  accepted branch and HEAD, target digest, target-binding digest, and
  postcondition digest.

#### Scenario: receipt-present cleanup is effect free

- **GIVEN** the exact immutable completion receipt is durable and cleanup is
  incomplete
- **WHEN** the same decision retries
- **THEN** ETHOS SHALL validate the exact decision, lane, head, receipt,
  postconditions, fence, and reservation binding and perform only idempotent
  cleanup
- **AND** it SHALL NOT repeat Git/worktree effect, rewrite the receipt, consult
  historical roots, or recreate effect authority.

#### Scenario: successful cleanup preserves ordering

- **GIVEN** the exact immutable completion receipt is durable
- **WHEN** ETHOS cleans ownerless coordination
- **THEN** it SHALL release the exact SQLite fence through compare-and-swap
  before deleting the visible ownerless reservation
- **AND** a failed or unverifiable fence release SHALL retain the visible
  reservation.

#### Scenario: effect-complete recovery precedes ordinary observation

- **GIVEN** the reservation state is `effect_complete_receipt_missing`
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
- **AND** the exception SHALL become `transition_unknown` with explicit
  reconciliation required.

#### Scenario: damaged fence payload preserves independent lease truth

- **GIVEN** the lease and closeout-fence stores are independently current
- **WHEN** one fence payload cannot be decoded or validated
- **THEN** state inventory SHALL report the fence projection as unverifiable
- **AND** it SHALL continue to report independently validated lease facts rather
  than rewriting the lease schema state as invalid.

#### Scenario: undeclared external lifecycle execution is rejected

- **GIVEN** the Work Lane lifecycle declares its allowed executable and state
  bindings
- **WHEN** a mandatory admission or effect path invokes an undeclared external
  executable
- **THEN** generic coupling audit SHALL fail before proof or land
- **AND** optional explicitly configured semantic-attestation and policy adapters
  outside lane-resolution effect authority SHALL remain unaffected.
