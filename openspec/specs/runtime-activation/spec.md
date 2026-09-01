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

ETHOS SHALL prepare each exact locked dependency closure once at its native
owner boundary. Python runtime activation SHALL fill and prove the Git-common
hashed Python supply before selector mutation. Source package construction
SHALL consume the repository-prepared OpenSpec production closure selected by
the exact `package-lock.json` without invoking npm, accessing the network, or
depending on an ambient npm cache.

#### Scenario: A locked artifact is absent from cache

- **WHEN** an exact hashed Python artifact is absent from the Git-common cache
- **THEN** hook installation fetches it during one owned pre-activation sync
- **AND** deletes the temporary sync target
- **AND** the immutable runtime installation succeeds with network access disabled.

#### Scenario: Cache fill fails

- **WHEN** the exact hashed Python closure cannot be fetched or installed
- **THEN** hook installation fails with the captured tool diagnostic
- **AND** selector, hook configuration, and SQLite state remain unchanged.

#### Scenario: Offline preflight passes

- **WHEN** the owned Git-common cache contains every locked Python artifact
- **THEN** runtime construction reuses the same exported requirements offline
- **AND** no activation step can discover or select a different closure.

#### Scenario: A prepared OpenSpec production closure is packaged

- **WHEN** wheel or sdist construction receives a prepared `node_modules` root
  matching every non-development, non-link package in the exact source lock
- **THEN** the build includes only those production package roots
- **AND** it invokes no npm command, reads no npm cache, opens no network route,
  and creates no second dependency tree.

#### Scenario: Prepared OpenSpec supply is absent or drifted

- **WHEN** a locked production package is absent, symlinked, has a different
  package version, or contains an undeclared nested package root
- **THEN** artifact construction fails before emitting an artifact
- **AND** the result identifies the exact package path and the single native
  provisioning action `npm ci --ignore-scripts`.

#### Scenario: A wheel is built from the source distribution

- **WHEN** the sdist is the source for a later wheel build
- **THEN** its packaged OpenSpec production closure is validated against the
  same lock and reused directly
- **AND** wheel construction requires neither registry access nor npm cache
  state.
