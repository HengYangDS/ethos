## ADDED Requirements

### Requirement: Attested compensation closes its forward effect

ETHOS SHALL treat an effect Attestation as closed when a later Attestation in
the same set records the exact inverse transaction under identical assertions
and passes historical validation. A closed effect SHALL NOT satisfy exact-plan
recognition or count as a Work Lane birth. Both Attestations SHALL remain
unchanged, and an unattested or invalid reversal SHALL NOT close an effect.

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

#### Scenario: Reversal is not an attested exact inverse

- **WHEN** the refs were restored without an Attestation, or the inverse
  Attestation fails historical validation
- **THEN** the forward Attestation still selects its plan
- **AND** the executor blocks with its content-mismatch gap instead of
  replaying the effect.
