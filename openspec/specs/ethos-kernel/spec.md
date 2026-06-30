# ETHOS Kernel

## Purpose

ETHOS SHALL model repository operation through Constitution, Subject,
Commitment, Change, Evidence, Chronicle, and Evolution.

## Requirements

### Requirement: Kernel Chain
ETHOS SHALL model repository operation through the chain Subject,
Commitment, Change, Evidence, Chronicle, and Evolution.

#### Scenario: Repository operation is represented
- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through kernel objects without
  depending on workspace, agent, adopter, or hosted-runner packages

### Requirement: Kernel Result Contract
ETHOS SHALL emit stable JSON result envelopes with `ok`, `summary`,
`diagnostics`, `required_gaps`, `next_actions`, and `data`.

#### Scenario: Automation reads command output
- **WHEN** an automation consumer requests JSON output from an ETHOS command
- **THEN** the response is one parseable object with the stable result fields

### Requirement: Deterministic Action Graph
ETHOS SHALL serialize action graphs deterministically, including validation gaps
for invalid graphs.

#### Scenario: Proof readiness is planned
- **WHEN** ETHOS plans or runs proof gates
- **THEN** selected gates are represented as ordered action graph nodes with
  explicit dependencies and validation gaps
