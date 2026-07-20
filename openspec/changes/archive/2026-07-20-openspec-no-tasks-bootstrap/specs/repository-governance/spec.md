## MODIFIED Requirements

### Requirement: OpenSpec Lifecycle Trust Review

ETHOS SHALL review OpenSpec lifecycle readiness in addition to official
OpenSpec CLI validation. An official `no-tasks` Change SHALL be treated as an
active, non-complete lifecycle carrier: it may bootstrap only its own absent
untracked `scope.toml` companion through the existing companion guard, but it
does not satisfy proposal, design, task, delta-spec, claim-binding, validation,
or proof requirements.

#### Scenario: Active OpenSpec change is lifecycle complete
- **GIVEN** an active OpenSpec change has proposal, design, tasks, and delta
  specs
- **AND** a trust-bearing active claim references that change
- **WHEN** ETHOS audits OpenSpec repository governance in lifecycle mode
- **THEN** ETHOS reports the change as lifecycle-ready

#### Scenario: Active OpenSpec change lacks claim binding
- **GIVEN** an active OpenSpec change has valid official OpenSpec syntax
- **AND** no active trust-bearing claim references that change
- **WHEN** ETHOS audits OpenSpec repository governance in lifecycle mode
- **THEN** ETHOS reports `openspec_claim_binding_missing:<change>`

#### Scenario: Newly created official Change bootstraps its scope companion
- **GIVEN** the official OpenSpec CLI reports one Change as `no-tasks`
- **AND** that Change has no tracked or malformed `scope.toml` companion
- **WHEN** prewrite evaluates only that exact Change-local `scope.toml` path
- **THEN** it treats the Change as active and admits the existing exact-one
  scope-bootstrap path
- **AND** an ordinary material path remains blocked until the valid companion
  declares coverage
- **AND** an `in-progress` Change remains preferred over `no-tasks`, while an
  unknown official status remains excluded.
