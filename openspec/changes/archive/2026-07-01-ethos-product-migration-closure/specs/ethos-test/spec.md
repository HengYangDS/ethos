## ADDED Requirements

### Requirement: Product Migration Closure Proof
ETHOS SHALL prove product migration closure through conformance tests, local
build smoke, npm launcher smoke, OpenSpec validation, parity evidence, and
execution-backed ETHOS proof.

#### Scenario: Closure proof runs
- **WHEN** product migration closure is verified
- **THEN** unit and architecture tests pass
- **AND** all Python packages build wheel and sdist locally
- **AND** npm launcher smoke and dry-run pack pass without publishing
- **AND** OpenSpec validation and ETHOS proof report no required gaps
