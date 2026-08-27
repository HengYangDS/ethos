## ADDED Requirements

### Requirement: Command results use one closed semantic envelope

Every public command result SHALL carry one authoritative, self-explanatory
verdict. `pass` SHALL carry no blocker; `unknown` SHALL name missing facts or
evidence; `block` SHALL name a failed condition or adverse diagnostic. A
projection SHALL NOT manufacture a verdict from facts-only data.

#### Scenario: Required facts are unavailable

- **WHEN** a required fact or evidence item is unavailable
- **THEN** the verdict is `unknown` and `required_gaps` names it.

#### Scenario: A condition blocks the operation

- **WHEN** an admitted precondition fails
- **THEN** the verdict is `block` with a named gap or adverse diagnostic.

#### Scenario: Work Lane validation is healthy

- **WHEN** workspace validation passes
- **THEN** `lane status` is `pass`; coordination advisories stay observations.
