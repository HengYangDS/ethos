## ADDED Requirements

### Requirement: ETHOS OpenSpec adapter remains under one command plane
ETHOS SHALL expose OpenSpec governance health through `ethos openspec --json`
and `ethos openspec --lifecycle --json` while keeping the public workflow
centered on `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`.

#### Scenario: OpenSpec adapter composes official and ETHOS checks
- **WHEN** `ethos openspec --lifecycle --json` runs
- **THEN** the payload includes official OpenSpec doctor, status, and strict
  validation results
- **AND** it includes ETHOS lifecycle carrier review for proposal, design,
  tasks, delta specs, capability profiles, claim bindings, evidence refs, and
  live-spec diff guards

#### Scenario: OpenSpec adapter does not become a second public command plane
- **WHEN** ETHOS reports OpenSpec governance gaps
- **THEN** the next action enters through an `ethos ...` command
- **AND** raw OpenSpec CLI commands remain adapter implementation detail or
  maintainer reference rather than the adopter first-hour workflow
