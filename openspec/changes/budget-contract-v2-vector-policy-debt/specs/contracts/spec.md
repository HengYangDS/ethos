## ADDED Requirements

### Requirement: Budget Contract v2 policy and debt are canonical typed contracts

ETHOS SHALL represent Budget Contract v2 policy as a strict discriminated union
with canonical digest-bound coordinate vectors and Debt v2 as a strict mapped or
unmapped discriminated union.

#### Scenario: Coordinate vectors cannot compensate or hide duplicates

- **WHEN** a v2 vector is parsed or canonically constructed
- **THEN** every `(scope_id, metric_id)` key SHALL be unique and stably ordered
- **AND** its unit SHALL be bound to that key
- **AND** its digest SHALL be recomputed from canonical validated coordinates
- **AND** no dictionary, scalar total, or cross-coordinate conversion SHALL fund
  another coordinate.

#### Scenario: Inactive policy carries no fabricated vectors

- **WHEN** complete immutable baseline evidence is unavailable
- **THEN** the repository v2 policy SHALL use `state = "inactive"`
- **AND** it SHALL NOT contain baseline or terminal vectors
- **AND** any unmapped debt SHALL carry no enforceable allowance.

### Requirement: Task 5 consumes the accepted Task 4 observation type

ETHOS SHALL expose the accepted Task 4 shadow observation as a public typed
contract and SHALL reuse it in Task 5 verdict inputs without duplicating replay,
snapshot, provider, coordinate, or digest models.

#### Scenario: Incomplete replay remains all-or-nothing

- **WHEN** a Task 4 observation has a null v2 payload, required gap, or non-reviewed
  comparison state
- **THEN** Task 5 SHALL emit no coordinate arithmetic or clean result.
