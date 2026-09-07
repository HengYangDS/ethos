## ADDED Requirements

### Requirement: Missing Work Lane coordination is reacquired without content mutation

ETHOS SHALL expose one public missing-Lease reacquisition through its existing
Lease lifecycle. It SHALL derive the exact linked Work Lane, current actor,
HEAD, index, working-content digest, and missing Lease from fresh observations.
Apply SHALL require explicit authorization and those exact coordinates, use
the existing four-field Lease transaction, preserve all Git and working content,
and record or recover the corresponding native effect Attestation. It SHALL
NOT treat the resulting Lease as OpenSpec intent, proof, or write admission.

#### Scenario: Dirty linked Work Lane has lost its Lease

- **WHEN** an explicitly selected registered Work Lane has no Lease and contains
  staged, unstaged, and untracked content
- **THEN** dry-run returns one exact reacquisition command without modifying it
- **AND** authorized apply acquires coordination for the invoking holder while
  retaining the same HEAD, index, and content bytes.

#### Scenario: Exact coordinates drift or a different owner appears

- **WHEN** the target HEAD, index, content, linkage, or absent-Lease observation
  changes before acquisition commits
- **THEN** ETHOS blocks or rolls back its acquisition without replacing the
  current holder or altering repository content.

#### Scenario: A repeated apply observes the exact valid Lease postimage

- **WHEN** the same exact reacquisition is repeated after its Lease was committed
- **THEN** ETHOS recognizes the current relation without advancing generation
- **AND** reuses matching effect evidence or records the recovered postimage
- **AND** a different generation or expiry is rejected even for the same holder.

#### Scenario: Missing Lease is reported before content admission

- **WHEN** status or prewrite finds a linked Work Lane without a Lease
- **THEN** its actionable guidance selects public reacquisition derivation
- **AND** it does not recommend creating a nested lane or declare content proved.
