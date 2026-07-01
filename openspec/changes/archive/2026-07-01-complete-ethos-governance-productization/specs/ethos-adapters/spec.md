## ADDED Requirements

### Requirement: Official OpenSpec Lifecycle Adapter
ETHOS SHALL compose official OpenSpec CLI output with ETHOS lifecycle carrier
checks without replacing official OpenSpec validation.

#### Scenario: OpenSpec adapter reports lifecycle carriers
- **WHEN** ETHOS audits OpenSpec self-governance
- **THEN** the report includes official CLI command results
- **AND** the report includes active change carrier facts for proposal, design,
  tasks, delta specs, claim binding, and archive readiness

### Requirement: Work Lane Claim Binding Projection
ETHOS SHALL expose Work Lane ownership as claim boundary evidence for
trust-bearing mutation.

#### Scenario: Work Lane has a claim binding
- **WHEN** ETHOS inspects a current `work/*` lane with a bound claim id
- **THEN** the lane report includes the claim id as boundary evidence
- **AND** the lane report does not mark the claim promoted by lane presence
  alone

#### Scenario: Work Lane lacks a claim binding
- **WHEN** ETHOS inspects a current `work/*` lane without a bound claim id
- **THEN** the lane report remains usable for local work
- **AND** trust-bearing closeout reports a missing claim-binding gap

### Requirement: Intake Adapter Projection Boundary
ETHOS SHALL keep intake and Backlog provider state as projection or intake
evidence rather than repository truth.

#### Scenario: Intake provider reports done state
- **WHEN** an intake provider reports a task as complete
- **THEN** ETHOS records the intake state as projection evidence
- **AND** ETHOS still requires claim admission, OpenSpec lifecycle readiness,
  executed proof, and promotion targets before trust closeout
