## MODIFIED Requirements

### Requirement: Attestations use one deterministic Git set carrier

The sole current Attestation carrier SHALL be a canonical hash-sharded Git tree selected by
`refs/ethos/attestations-set`. Its root SHALL be a deterministic parentless commit over fixed
metadata. An update SHALL be exactly the observed set without the members whose lifetime has ended,
united with validated canonical members, followed by exact CAS. A member whose canonical bytes
exceed 1 MiB SHALL NOT be added.

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
- **AND** an operation still validates predicate, payload, relations, verifier, bindings, validity,
  and selected Commitment

#### Scenario: A member exceeds the size bound

- **WHEN** a writer offers a member whose canonical bytes exceed 1 MiB
- **THEN** the update fails closed with `attestation_member_too_large`
- **AND** the selected root is unchanged

#### Scenario: Ended members leave the set

- **WHEN** an update observes members whose lifetime has ended
- **THEN** the new root omits them and keeps every member whose lifetime continues
- **AND** a writer that loses the CAS race recomputes both the removal and the union

## ADDED Requirements

### Requirement: Attestation evidence bytes use released local custody

ETHOS SHALL store evidence bytes outside the Attestation set, in a content-addressed store in the
Git common directory that is never tracked or published. A member SHALL bind each stored file as
`custody:sha256:<digest>` in its evidence references. Stored bytes SHALL be deleted once no selected
member binds their digest.

#### Scenario: Evidence is recorded

- **WHEN** a record declares `custody:sha256:<digest>` and supplies a file with exactly that digest
- **THEN** the file is stored byte-exact under its digest and the member is added
- **AND** the worktree index, tracked files and remotes are unchanged

#### Scenario: Declared evidence is missing or differs

- **WHEN** a declared custody digest has neither stored bytes nor a supplied file with that digest
- **THEN** the record fails closed before any effect

#### Scenario: Evidence is released

- **WHEN** the last selected member that binds a custody digest leaves the set
- **THEN** the stored bytes for that digest are deleted
- **AND** bytes still bound by another member remain

#### Scenario: A record races the deletion of its evidence

- **WHEN** a record binds bytes that a concurrent update is deleting
- **THEN** the record waits for the deletion and stores its bytes again
- **AND** a cleanup failure after a swap is reported without failing the update
