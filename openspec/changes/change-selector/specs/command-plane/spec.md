## ADDED Requirements

### Requirement: An explicit Change binds one invocation

`ethos status`, `plan`, `prove`, `land` and `lane prewrite` SHALL accept `--change <id>`, and the
MCP `status`, `plan` and `land` tools SHALL accept `change`. An explicit Change SHALL take
precedence over the inherited `ETHOS_CHANGE` for every reader of the invocation and every child
process it starts, and SHALL NOT outlive the invocation.

#### Scenario: An explicit Change wins over the environment

- **GIVEN** a Work Lane with two active Changes and `ETHOS_CHANGE` naming one of them
- **WHEN** `lane prewrite`, `status` or `land` runs with `--change` naming the other
- **THEN** the command acts on the explicitly selected Change
- **AND** a child process of the invocation observes the same Change

#### Scenario: The selection ends with its invocation

- **WHEN** an invocation with an explicit Change returns or fails
- **THEN** the inherited `ETHOS_CHANGE`, or its absence, is restored
- **AND** the next MCP call without `change` observes no earlier selection
