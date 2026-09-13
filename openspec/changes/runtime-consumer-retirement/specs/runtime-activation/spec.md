## MODIFIED Requirements

### Requirement: Runtime activation includes Git-common state

ETHOS SHALL treat runtime selection, hook configuration and the Git-common
Lease schema as one activation transition. Successful activation SHALL leave
all three mutually readable; failed activation SHALL restore their exact prior
state. Later reclamation SHALL preserve successful activation and report its
independent completed, retained or deferred effects.

#### Scenario: Exact legacy Lease state is migrated

- **GIVEN** the previous canonical Lease table and internally consistent rows
- **WHEN** hook installation activates a new runtime
- **THEN** each row preserves only lane, holder, generation and expiry
- **AND** the new runtime can execute `ethos status --json` immediately.

#### Scenario: Activation fails after state migration is staged

- **WHEN** selector or hook configuration activation fails
- **THEN** the SQLite transaction rolls back
- **AND** selector bytes, Git configuration, database bytes and sidecar absence equal their pre-state.

#### Scenario: Successful activation has deferred reclamation

- **WHEN** the runtime, hooks and state have activated successfully but reclamation cannot finish
- **THEN** the result preserves the successful activation observation
- **AND** it reports the precise reclamation boundary and a fresh public recovery action without undoing completed effects.
