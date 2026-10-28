## MODIFIED Requirements

### Requirement: The binding uses only ETHOS-defined files

The tracked `.ethos/` binding SHALL contain only `profile.toml`, `workspace.toml`, `release.toml` and `rules.toml`. A repository SHALL declare its own proof gates in `profile.toml` or in the gate registry file its profile names, and receives the shared obligations its facts select. `workspace.toml` SHALL declare only `[commit_policy]`, and a repository that declares none SHALL NOT track it.

#### Scenario: A legacy binding file is tracked

- **WHEN** `.ethos/assistants.toml`, `.ethos/project.toml` or `.ethos/gates.toml` is tracked
- **THEN** the paradigm reports a binding file outside the ETHOS schema set.

#### Scenario: A profile names its own gate registry

- **WHEN** a profile names a tracked registry file outside `.ethos/`, such as `system/repository-gates.toml`
- **THEN** the repository's proof gates are that file's gates plus the shared obligations its facts select
- **AND** the registry's path does not change which shared obligations apply

#### Scenario: A workspace declares a table no reader consults

- **WHEN** `.ethos/workspace.toml` declares `[[package]]`
- **THEN** the paradigm reports the table and the repair deletes it.

#### Scenario: A workspace binding declares nothing else

- **WHEN** `.ethos/workspace.toml` declares only `[branch_roles]` with `release_mirror = "independent"`
- **THEN** the repair deletes `.ethos/workspace.toml`.
