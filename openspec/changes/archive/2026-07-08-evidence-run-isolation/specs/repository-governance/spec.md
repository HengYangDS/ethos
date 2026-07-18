## ADDED Requirements

### Requirement: Generated Evidence Boundary
ETHOS SHALL keep generated proof artifacts outside repository truth while making
latest-artifact writes deterministic enough for proof gates.

#### Scenario: Shared coverage evidence writes are serialized

- **WHEN** the Python owner test gate writes generated coverage evidence
- **THEN** it serializes cleanup, shard combination, and latest XML writes for
  the shared coverage evidence directory
- **AND** the serialization mechanism does not create a new repository truth
  store
- **AND** local fallback evidence does not claim hosted CI success.
