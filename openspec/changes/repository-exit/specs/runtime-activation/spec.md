## ADDED Requirements

### Requirement: Installation records the configuration it replaces

When `ethos hook install` adopts a repository whose Git-common hooks path ETHOS does not own, it SHALL record the hooks-related configuration it replaces, in the common and worktree scopes, with an absent value recorded as absent. It SHALL write the record within the activation, so a failed activation leaves none, and SHALL NOT rewrite a record that already exists.

#### Scenario: A repository with its own hooks adopts ETHOS

- **GIVEN** a repository whose `core.hooksPath` names its own hooks directory
- **WHEN** `ethos hook install` activates a runtime
- **THEN** the record names that hooks path
- **AND** a later upgrade leaves the record unchanged.

#### Scenario: A repository without a hooks path adopts ETHOS

- **WHEN** `ethos hook install` activates a runtime in a repository without `core.hooksPath`
- **THEN** the record holds the hooks path as absent.

### Requirement: A repository exit is previewed before any effect

`ethos adopt --exit` SHALL report, without any effect, the configuration it would restore, the selectors it would remove with their hashes, each linked worktree's hooks path, the Lease snapshot and a plan digest over them. It SHALL name a valid or unknown Lease, a held selection lock or a held proof slot as a blocker, and SHALL require the user's choice when no recorded configuration exists rather than guess it.

#### Scenario: An exit is inspected

- **WHEN** `ethos adopt --exit --json` runs in an adopted repository with a recorded configuration
- **THEN** it reports the restoration, the selector hashes and a plan digest
- **AND** no file, configuration or selector changes.

#### Scenario: No configuration was recorded

- **WHEN** the repository was adopted before installation recorded its configuration
- **THEN** the exit preview requires the user's choice instead of unsetting the hooks path.

#### Scenario: A lane holds a live Lease

- **WHEN** a Work Lane of the repository holds a valid Lease
- **THEN** the exit preview names that Lease as a blocker
- **AND** its plan digest differs from one made before the Lease.
