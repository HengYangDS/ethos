# ETHOS Command Plane

## Purpose

ETHOS SHALL expose the public command plane without owning repository lifecycle
semantics.
## Requirements
### Requirement: Public Command Plane
ETHOS SHALL keep the normal user workflow under five transition commands:
`ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`.

#### Scenario: Command surface is classified
- **WHEN** `ethos quality command-registry --json` runs
- **THEN** it reports five public workflow commands
- **AND** it reports `ethos report` as a scorecard command
- **AND** maintainer/reference commands are not counted as advanced public
  workflow commands

### Requirement: CLI Surface Delegation
The CLI SHALL compose output and UX while delegating semantics to core,
contracts, repository, assistants, and adapters packages.

#### Scenario: CLI package is scanned
- **WHEN** architecture tests inspect imports
- **THEN** the public CLI imports target product packages and does not import
  retired migration-host modules

### Requirement: Retired Family Command Vocabulary
ETHOS SHALL reject retired family-style command prefixes from governed docs.

#### Scenario: Retired capability command appears
- **WHEN** governed docs contain `ethos governance`, `ethos workspace`,
  `ethos agent`, `ethos project`, `ethos kernel`, or `ethos node` as a command
- **THEN** `ethos quality command-registry --json` reports a required gap

### Requirement: Proof Command State Semantics
ETHOS CLI SHALL present proof command states according to execution depth.

#### Scenario: Planning proof is ready
- **WHEN** `ethos prove --json` completes without executing gates
- **THEN** the CLI reports `ok=true` and `state=ready` for successful readiness
- **AND** the CLI reports `executed=false`

#### Scenario: Executed proof is proven
- **WHEN** `ethos prove --execute --json` completes with all gates passing
- **THEN** the CLI reports `ok=true` and `state=proven`
- **AND** the CLI reports `executed=true`

### Requirement: Self OpenSpec Lifecycle Mode
ETHOS CLI SHALL expose OpenSpec lifecycle review through the public ETHOS
command plane.

#### Scenario: OpenSpec lifecycle is audited
- **WHEN** `ethos openspec --lifecycle --json` runs
- **THEN** the CLI reports official OpenSpec validation and ETHOS lifecycle
  carrier readiness in one result envelope

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

### Requirement: Explain Command Projects Invalid-State Signals

ETHOS SHALL expose `ethos explain` as a read-only invalid-state taxonomy
projection for governance gaps and advisory signals.

#### Scenario: Explain accepts advisory signals without required-gap overclaim

- **WHEN** `ethos explain <signal> --json` runs for a non-blocking advisory signal
- **THEN** the payload keeps the original string as `gap` for compatibility
- **AND** the payload also exposes the original string as `signal`
- **AND** the payload classifies the signal into an invalid-state category
- **AND** the payload wording does not claim every explained signal is a required gap
- **AND** the taxonomy projection does not become a lifecycle command

#### Scenario: Explain help and docs use gap-or-signal language

- **WHEN** a human or agent reads `ethos explain --help` or the command-plane reference
- **THEN** the command is described as explaining a governance gap or advisory signal
- **AND** docs show `ethos explain <gap-or-signal>` rather than a required-gap-only surface
- **AND** the command remains a read-only projection, not a lifecycle command
