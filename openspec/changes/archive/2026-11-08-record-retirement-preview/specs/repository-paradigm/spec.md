## MODIFIED Requirements

### Requirement: Tunable values are declared parameters

Every value ETHOS applies that a repository may change SHALL be declared once in the paradigm with
its default, unit and bound. A binding MAY declare its own value in `rules.toml`
`[paradigm.<group>]`: a lower value applies, and a higher one within the bound with a reason in
`[paradigm.<group>.reasons]`; a floor row applies only higher values, without a reason. Any other
declaration SHALL be a gap that leaves the default in force. Product code SHALL read each value
through the declaration.

#### Scenario: A repository needs a longer gate budget

- **WHEN** a binding declares `timeout.gate_seconds = 1200` with a reason
- **THEN** each of the repository's gates without its own timeout runs under 1,200 seconds
- **AND** its proofs list that value with the reason.

#### Scenario: A higher value has no reason or exceeds the bound

- **WHEN** a binding declares a higher `timeout` value without a reason, or one beyond its bound
- **THEN** the paradigm reports the declaration and the default stays in force.

#### Scenario: A lower value

- **WHEN** a binding declares a lower `timeout.git_seconds`
- **THEN** it applies without a reason.

#### Scenario: Product code restates a timeout

- **WHEN** product code binds a numeric literal to a wait, as a timeout argument or a duration
  constant
- **THEN** ETHOS's architecture check reports the file and line.

#### Scenario: A retention floor

- **WHEN** a binding declares a higher `retention.record_seconds` without a reason, or a lower one
- **THEN** the higher value applies, and the lower one is a gap that leaves the default in force
