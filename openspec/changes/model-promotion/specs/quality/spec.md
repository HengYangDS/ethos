## ADDED Requirements

### Requirement: One commit semantics owner

Lifecycle message generation, commit-msg admission, source proof, hosted proof, and history validation SHALL consume one repository-declared positive commit policy. ETHOS SHALL NOT add a compatibility whitelist, second grammar, wrapper requirement, or hard-coded adopter tool.

#### Scenario: Lifecycle creates an archive commit

- **WHEN** ETHOS generates the archive subject
- **THEN** the subject is produced through the same declared policy consumed by commit-msg admission

### Requirement: Positive gate topology is complete

Each required gate SHALL declare exactly one policy owner, executor inputs,
contract evidence, material roots, resource isolation, command/environment
contract, and tests/evidence consumer. Profile lint and scaffold SHALL derive
from this contract rather than requiring adopters to guess fields.

#### Scenario: Gate declaration is packaged

- **WHEN** source and package registries are validated
- **THEN** they satisfy the same strict schema and digest
- **AND** missing topology fields produce exact field paths and one migration or
  declaration command

### Requirement: Quality budgets are explicit positive policy

The ETHOS product profile SHALL enforce at least 95 percent coverage and a
`python_tests` source budget of 36000 through their unique tracked policy owners.
Commit grammar, editor formatting, supply-chain authority, and material roots
SHALL likewise have one positive owner each.

#### Scenario: A proof claims product acceptance

- **WHEN** full proof executes at an exact HEAD
- **THEN** coverage and source budget evidence identify their owner, measured
  value, threshold, material scope, and executor result
- **AND** no whitelist, baseline suppression, or generated exception substitutes
  for passing policy

### Requirement: Authority and projection carriers change together

Profile policy SHALL declare repository-owned authorities and derived carriers
whose consistency and atomic Change scope are compiled by the existing gate
graph without hard-coded tool semantics.

#### Scenario: A tool version or trust authority changes alone

- **WHEN** its lock, workflow, image, generated config, test, or documentation
  projection is missing, stale, or outside the same Change
- **THEN** plan, prewrite, or prove blocks at the earliest enforceable boundary
