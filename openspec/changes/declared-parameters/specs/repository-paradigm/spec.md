## ADDED Requirements

### Requirement: Tunable values are declared parameters

Every value that ETHOS applies and a governed repository may need to change SHALL be declared once
in the paradigm with its default, unit and bound. A binding MAY declare its own value in
`rules.toml` `[paradigm.<group>]`: a lower value applies, and a higher one applies within the bound
with a reason in `[paradigm.<group>.reasons]`. Any other declaration SHALL be a gap that leaves the
default in force. Product code SHALL read each value through the declaration, never as a literal.

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

- **WHEN** product code passes a numeric literal as a command timeout or names a timeout constant
- **THEN** ETHOS's architecture check reports the file and line.
