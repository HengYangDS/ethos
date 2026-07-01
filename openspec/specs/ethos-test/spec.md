# ETHOS Test

## Purpose

ETHOS SHALL keep conformance, parity, sample repository, schema compatibility,
and migration replay proof separate from runtime packages.

## Requirements

### Requirement: Proof Separation
ETHOS SHALL host conformance fixtures and parity proof helpers outside the
runtime semantic packages.

#### Scenario: Conformance package is inspected
- **WHEN** tests inspect `ethos-test`
- **THEN** it contains proof fixtures and sample helpers rather than runtime
  command semantics

### Requirement: Shadow Parity Evidence
ETHOS SHALL require tracked shadow parity evidence before declaring adopter or
generic migration parity closed.

#### Scenario: Parity gaps are checked
- **WHEN** `ethos parity gaps --adopter <name> --json` runs
- **THEN** tracked shadow evidence must name verified capabilities and report
  no required gaps before migrated or split parity rows are closed

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
