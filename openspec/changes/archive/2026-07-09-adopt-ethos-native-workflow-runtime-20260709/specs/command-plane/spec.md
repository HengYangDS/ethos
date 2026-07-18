## MODIFIED Requirements

### Requirement: Public Command Plane
ETHOS SHALL expose `status`, `plan`, `prove`, `land`, and `publish` as the
trust-bearing transition commands.

#### Scenario: Workflow runtime projection is reported
- **WHEN** `ethos plan --json` or `ethos report --json` projects workflow runtime state
- **THEN** the projection is nested under existing command payloads
- **AND** it does not add a new public lifecycle command
- **AND** it references the same transition commands, guards, and evidence boundaries as the ETHOS command plane

### Requirement: ETHOS OpenSpec adapter remains under one command plane
ETHOS SHALL wrap official OpenSpec validation and ETHOS lifecycle checks under
ETHOS commands without making OpenSpec a second public command plane.

#### Scenario: Runtime adoption uses OpenSpec as carrier
- **WHEN** workflow runtime semantics are changed
- **THEN** an OpenSpec change carrier records the intent and deltas
- **AND** official OpenSpec validation remains carrier validation rather than runtime authority
