## MODIFIED Requirements

### Requirement: Command results use one closed semantic envelope

Every public command result SHALL carry one authoritative verdict and SHALL be
self-explanatory at the typed boundary. `pass` SHALL carry no blocking gap or
adverse diagnostic. `unknown` SHALL name at least one missing fact or evidence
item. `block` SHALL name at least one failed condition or carry an adverse
diagnostic. A projection SHALL NOT manufacture a verdict from a facts-only
mapping.

#### Scenario: Required facts are unavailable

- **WHEN** a command cannot determine a required fact or evidence item
- **THEN** the result verdict is `unknown`
- **AND** `required_gaps` names the missing fact or evidence.

#### Scenario: A known condition blocks the operation

- **WHEN** a current fact violates an admitted precondition
- **THEN** the result verdict is `block`
- **AND** a required gap or adverse diagnostic identifies the reason.

#### Scenario: Work Lane facts and validation are healthy

- **WHEN** `lane status` observes a valid workspace and its schema validation passes
- **THEN** the public verdict is `pass`
- **AND** coordination advisories remain observations rather than being promoted
  into a reasonless `unknown` verdict.
