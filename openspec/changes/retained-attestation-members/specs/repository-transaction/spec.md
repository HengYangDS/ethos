## RENAMED Requirements

- FROM: `### Requirement: Attested compensation closes its forward effect`
- TO: `### Requirement: An attested reversal closes its forward effect`

## MODIFIED Requirements

### Requirement: An attested reversal closes its forward effect

ETHOS SHALL treat an effect Attestation as closed when a later Attestation in
the same set, observed after the effect completed, sets every ref of the effect
back to the value it expected and passes historical validation. The exact
inverse and a Work Lane retirement both qualify, whatever they assert. A closed
effect SHALL NOT satisfy exact-plan recognition or count as a Work Lane birth.
Both Attestations SHALL remain unchanged, and an unattested or invalid reversal
SHALL NOT close an effect.

#### Scenario: Identical plan after attested compensation

- **WHEN** an applied ref effect was compensated through an attested exact
  inverse and the identical plan is requested again
- **THEN** the executor re-admits the current refs and applies the
  compare-and-swap again
- **AND** the earlier forward and inverse Attestations remain in the set.

#### Scenario: Work Lane restarts after a compensated start

- **WHEN** a Work Lane start was compensated through an attested exact inverse
  and the same branch later starts from another candidate head
- **THEN** Change provenance reads only the uncompensated start as the lane
  birth.

#### Scenario: Work Lane starts again after its retirement

- **WHEN** a Work Lane was retired through an attested deletion of its branch
  and the same name later starts from the same candidate head
- **THEN** the executor applies the identical start plan again
- **AND** Change provenance reads only the new start as the lane birth.

#### Scenario: Reversal is not an attested exact inverse

- **WHEN** the refs were restored without an Attestation, or the inverse
  Attestation fails historical validation
- **THEN** the forward Attestation still selects its plan
- **AND** the executor blocks with its content-mismatch gap instead of
  replaying the effect.
