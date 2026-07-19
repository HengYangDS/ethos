## ADDED Requirements

### Requirement: Bounded readers defer foreign detail without manufacturing zero

ETHOS SHALL preserve the bounded-reader performance contract while explicitly
distinguishing unobserved foreign Work Lane detail from observed zero.

#### Scenario: Bounded status and orient expose deferred aggregates

- **WHEN** bounded status or orientation skips foreign dirty-state and history
  inspection
- **THEN** coordination SHALL report `detail_state=deferred`
- **AND** dirty, overlap, unknown-scope, closeout-residue, and dirty-residue
  aggregate counts SHALL be null rather than zero
- **AND** human output SHALL direct the operator to `ethos lane status --json`
  for exact detail.

#### Scenario: Full lane status retains exact aggregates

- **WHEN** `ethos lane status --json` performs full foreign Work Lane inspection
- **THEN** coordination SHALL report `detail_state=exact`
- **AND** all aggregate counts SHALL remain non-negative integers
- **AND** foreign or dirty visibility SHALL NOT authorize cleanup or retirement.

### Requirement: Local publication consumes current product blockers

ETHOS product publication readiness SHALL combine executed proof with current
hard-quality observations rather than treating either source as independently
sufficient.

#### Scenario: Current hard-quality blocker overrides prior proof

- **GIVEN** the current HEAD has an executed proof record
- **WHEN** the current product hard-quality floor reports a required gap
- **THEN** `ethos publish --json` SHALL report local readiness false and include
  that exact gap
- **AND** it SHALL NOT perform or claim remote publication.
