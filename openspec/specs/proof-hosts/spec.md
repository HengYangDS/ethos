# ETHOS Proof Hosts

## Purpose

ETHOS SHALL keep conformance, parity, sample repository, schema compatibility,
and migration replay proof separate from runtime packages.
## Requirements
### Requirement: Proof Separation
ETHOS SHALL host conformance fixtures and parity proof helpers outside the
runtime semantic packages.

#### Scenario: Conformance package is inspected
- **WHEN** tests inspect `proof-hosts`
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

### Requirement: Governance Lifecycle Fixtures
ETHOS SHALL provide reusable tests and fixtures for complete and malformed
governance lifecycles.

#### Scenario: Complete lifecycle fixture passes
- **WHEN** tests load a complete governance lifecycle fixture
- **THEN** claim admission, OpenSpec lifecycle review, proof evidence, and
  promotion target validation all report no required gaps

#### Scenario: Malformed lifecycle fixture fails
- **WHEN** tests load a malformed governance lifecycle fixture
- **THEN** ETHOS reports specific required gaps for missing claim binding,
  missing promotion target, missing executed proof, or malformed OpenSpec
  carrier state

### Requirement: Reference Adopter Boundary Fixtures
ETHOS SHALL test adopter parity through generic profiles instead of core
package adopter terminology.

#### Scenario: Reference adopter fixture is validated
- **WHEN** tests validate a reference adopter profile fixture
- **THEN** adopter-specific terms remain in the fixture or evidence
- **AND** core product packages remain provider-neutral

### Requirement: Skills V2 Conformance Fixtures

ETHOS SHALL keep Skills V2 conformance, migration replay, and parity fixtures
outside runtime semantic packages.

#### Scenario: placeholder skill is rejected

- **WHEN** Skills V2 conformance tests run against a minimal placeholder
  `SKILL.md`
- **THEN** the fixture reports required quality gaps

#### Scenario: adopter migration replay remains readable

- **WHEN** Skills V2 migration replay tests run against ETHOS v1, a reference-adopter v1, and
  external style activation records
- **THEN** each input normalizes into the provider-neutral IR without losing
  historical fixture fields

### Requirement: Hosted provider observations remain evidence-class scoped

ETHOS SHALL capture hosted provider observation envelopes without treating local
tool discovery or provider CLI output as repository proof.

#### Scenario: Provider observation envelope is captured

- **WHEN** hosted provider observation runs in dry-run or execute mode
- **THEN** the evidence SHALL name GitHub and GitLab provider observation state
- **AND** it SHALL include the Git head, remote URL, command, tool availability,
  and execution state
- **AND** it SHALL explicitly set hosted GitHub status claimed, hosted GitLab
  status claimed, and remote publication claimed to false unless separate hosted
  facts are promoted through the publication evidence class.
