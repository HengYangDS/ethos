## ADDED Requirements

### Requirement: Python test basetemp has one explicit owner

An ETHOS Python gate SHALL distinguish owned from caller-supplied temporary paths.

#### Scenario: Internally allocated Python test basetemp is reclaimed

- **WHEN** the Python test gate allocates its default pytest basetemp
- **THEN** the gate records that it owns the path
- **AND** it removes that exact path after successful or failed execution
- **AND** cleanup failure remains visible.

#### Scenario: Caller-managed Python test basetemp is preserved

- **WHEN** `ETHOS_TEST_BASETEMP` supplies the pytest basetemp
- **THEN** the gate records that the path is externally managed
- **AND** it never recursively removes that path.
