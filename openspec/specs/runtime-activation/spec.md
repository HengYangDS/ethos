# runtime-activation Specification

## Purpose
Define atomic activation of immutable ETHOS runtimes, hooks, configuration,
and Git-common Lease state so upgrades either become mutually readable or
leave the prior installation unchanged.

## Requirements

### Requirement: Runtime activation includes Git-common state

ETHOS SHALL treat runtime selection, hook configuration, and the Git-common
Lease schema as one activation transition. A successful installation SHALL
leave all three mutually readable; a failed installation SHALL restore their
exact prior state.

#### Scenario: Exact legacy Lease state is migrated

- **GIVEN** the previous canonical Lease table and internally consistent rows
- **WHEN** hook installation activates a new runtime
- **THEN** each row preserves only lane, holder, generation, and expiry
- **AND** the new runtime can execute `ethos status --json` immediately.

#### Scenario: Activation fails after state migration is staged

- **WHEN** selector or hook configuration activation fails
- **THEN** the SQLite transaction rolls back
- **AND** selector bytes, Git configuration, database bytes, and sidecar absence equal their pre-state.

### Requirement: Incompatible state has one public recovery

ETHOS SHALL block before activation when legacy state cannot be projected
without ambiguity and SHALL provide one explicit authorized reset command.

#### Scenario: Legacy row is malformed or contradictory

- **WHEN** redundant legacy columns and payload disagree or required terminal values are invalid
- **THEN** installation performs no selector, hook configuration, or state effect
- **AND** status and install report `ethos hook install --reset-state --authorize --json` as the sole next action.

#### Scenario: Reset is authorized

- **WHEN** the operator executes the exact authorized reset command
- **THEN** only the obsolete Lease relation is replaced by the empty terminal relation inside the activation transaction
- **AND** existing Git refs and worktrees remain untouched and observable as unbound.

### Requirement: Locked closure self-heals before activation

ETHOS SHALL fill the Git-common cache from the exact locked runtime dependency
closure and then prove that closure by installing it offline before changing
selector, hooks, Git configuration, or SQLite state.

#### Scenario: A locked artifact is absent from cache

- **WHEN** an exact hashed artifact is absent from the Git-common cache
- **THEN** hook installation fetches it during one owned pre-activation sync
- **AND** deletes the temporary sync target
- **AND** the immutable runtime installation succeeds with network access disabled.

#### Scenario: Cache fill fails

- **WHEN** the exact hashed closure cannot be fetched or installed
- **THEN** hook installation fails with the captured tool diagnostic
- **AND** selector, hook configuration, and SQLite state remain unchanged.

#### Scenario: Offline preflight passes

- **WHEN** the owned cache contains every locked artifact
- **THEN** runtime construction reuses the same exported requirements offline
- **AND** no activation step can discover or select a different closure.
