# ETHOS CLI

## Purpose

ETHOS SHALL expose the public command plane without owning repository lifecycle
semantics.
## Requirements
### Requirement: Public Command Plane
ETHOS SHALL keep the normal user workflow under `ethos ...` commands and keep
retired root commands out of current user-facing docs.

#### Scenario: Command examples are checked
- **WHEN** `ethos quality command-examples --json` scans current docs
- **THEN** examples use the ETHOS command plane or explicitly allowed
  non-ETHOS tooling roots

### Requirement: CLI Surface Delegation
The CLI SHALL compose output and UX while delegating semantics to core,
contracts, repository, assistants, and adapters packages.

#### Scenario: CLI package is scanned
- **WHEN** architecture tests inspect imports
- **THEN** the public CLI imports target product packages and does not import
  retired migration-host modules

### Requirement: Retired Family Command Vocabulary
ETHOS SHALL reject retired family-style command prefixes from current docs.

#### Scenario: Retired family command appears
- **WHEN** current docs contain `ethos governance`, `ethos workspace`,
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
- **WHEN** `ethos self openspec --lifecycle --json` runs
- **THEN** the CLI reports official OpenSpec validation and ETHOS lifecycle
  carrier readiness in one result envelope
