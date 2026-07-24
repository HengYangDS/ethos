## ADDED Requirements

### Requirement: Budget Contract v2 verdicts are pure and non-compensating

ETHOS SHALL compile Budget Contract v2 verdicts from typed observations, typed
policy, and an explicit calendar date without filesystem, Git, configuration,
environment, or clock reads.

#### Scenario: One coordinate breach blocks transition policy

- **WHEN** one observed coordinate exceeds its same-coordinate allowance while
  another coordinate is below its allowance
- **THEN** the exceeded coordinate SHALL remain blocking
- **AND** no surplus, different unit, or different scope SHALL compensate it.

#### Scenario: Invalid debt contributes zero allowance

- **WHEN** debt is unmapped, expired, overdue, stale, replay-mismatched, or invalid
- **THEN** it SHALL contribute zero allowance
- **AND** the verdict SHALL contain a stable blocking gap.

### Requirement: Repository Budget Contract v2 activation is explicit

ETHOS SHALL keep the tracked v2 repository policy inactive until complete
immutable baseline/terminal vectors and replay bindings exist.

#### Scenario: Node-runtime successor remains unmapped

- **WHEN** the historical node-runtime record lacks exact admitted HEAD, scope,
  inventory, baseline-snapshot, or historical-replay binding
- **THEN** its v2 successor SHALL use `mapping_state = "unmapped"`
- **AND** the missing bindings SHALL remain explicit and blocking
- **AND** v1 authority SHALL remain unchanged.
