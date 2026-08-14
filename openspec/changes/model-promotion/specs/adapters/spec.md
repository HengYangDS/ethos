## ADDED Requirements

### Requirement: Attestations use one deterministic Git set carrier

The sole current Attestation carrier SHALL be a canonical hash-sharded Git tree
selected by `refs/ethos/attestations-set`. Its root SHALL be a deterministic
parentless commit over fixed metadata. An update SHALL be exactly the union of
the observed set and validated canonical members followed by exact CAS.

#### Scenario: Concurrent writers add different Attestations

- **WHEN** one writer loses the set-ref CAS race
- **THEN** it re-observes the selected set and recomputes the deterministic union
- **AND** the successful root contains both immutable members

#### Scenario: A member is added repeatedly or collides

- **WHEN** canonical bytes for an existing identity are added again
- **THEN** the root is unchanged
- **AND** different bytes for the same identity fail closed

#### Scenario: Set membership is evaluated

- **WHEN** an Attestation exists in the selected set
- **THEN** membership proves preservation only
- **AND** an operation still validates predicate, payload, relations, verifier,
  bindings, validity, and selected Commitment

### Requirement: Non-authoritative Attestation stores are not current readers

Git-common JSON directories and operation indexes MAY stage or cache bytes but
SHALL NOT select current Attestations or authorize effects after cutover.
Historical Claim and Chronicle bytes SHALL remain inert Git history.

#### Scenario: A stale local Attestation exists

- **WHEN** it is absent from the selected Git set
- **THEN** status, planning, proof, and effects ignore it as current evidence
- **AND** no compatibility scan silently promotes it
