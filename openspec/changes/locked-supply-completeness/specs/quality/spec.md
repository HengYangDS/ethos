## ADDED Requirements

### Requirement: Locked supply is complete before ETHOS uses it

Before ETHOS returns a locked tool or a locked environment, native mise SHALL report, in the same isolated safe-mode resolution, every declared tool installed at its locked version with an existing install path, and an executable that a declared tool provides under its own name SHALL resolve inside that tool's install path. Otherwise resolution SHALL refuse with a gap that names each missing tool or the executable outside its tool, and SHALL NOT return another tool's executable in its place.

#### Scenario: A declared tool is not installed

- **WHEN** a repository locks a tool that native mise reports as not installed at its locked version
- **THEN** a locked tool or environment for that repository is refused with `mise_supply_incomplete` naming that tool
- **AND** no executable of another tool, such as Node's bundled npm for a locked npm, is returned

#### Scenario: Another tool supplies a declared tool's executable

- **WHEN** an executable that a declared tool provides under its own name resolves inside another tool's install path
- **THEN** resolution is refused with `mise_executable_outside_tool` naming that executable

#### Scenario: A complete supply

- **WHEN** every declared tool is installed at its locked version
- **THEN** resolution returns the locked tool or environment
- **AND** an executable that no declared tool names, such as npm where only node is declared, resolves as native mise selects it

### Requirement: A locked supply refusal names the action that can help

A refusal of incomplete locked supply SHALL name the next action that can complete it. When the selected mise's safe mode drops the dependency graph that a missing tool's lock entry references, as mise does from 2026.11.0, the refusal SHALL name that regression and an earlier mise instead of `mise trust`.

#### Scenario: The selected mise drops the locked graph

- **WHEN** the selected mise is 2026.11.0 or later and a missing tool's lock entry references a dependency graph
- **THEN** the refusal names that regression and an earlier mise
- **AND** it does not name `mise trust`

#### Scenario: Trust can select the locked install

- **WHEN** a missing tool's root is not trusted and the selected mise can use trust-keyed lock metadata in safe mode
- **THEN** the refusal names `mise trust` as the next action

#### Scenario: The supply is not installed

- **WHEN** a trusted root's declared tool is not installed
- **THEN** the refusal names `mise install --locked` as the next action

## MODIFIED Requirements

### Requirement: Disposable mise copies carry only native trust

Resolution and provisioning SHALL carry to their disposable copy of the exact declared bytes only the trust that native mise, under the caller's own trust inputs, already reports for the repository's configuration, and only for that invocation. They SHALL write no trust record and SHALL NOT trust a configuration that native mise does not report as trusted. A refusal for an untrusted configuration SHALL name native `mise trust` where trust can select the locked install.

#### Scenario: A trusted configuration locks a trust-keyed install

- **WHEN** native mise reports the repository's configuration as trusted, and it locks a tool whose installed copy is keyed by trust-only lock metadata such as an aube entry
- **THEN** resolution selects that installed copy
- **AND** no repository code runs and no trust record is written

#### Scenario: A trusted configuration provisions a locked tool

- **WHEN** native mise reports the repository's configuration as trusted, and ETHOS provisions a locked tool whose archive is not cached
- **THEN** the one native install in the disposable copy reads that copy's lock
- **AND** no trust record is written

#### Scenario: An untrusted configuration

- **WHEN** native mise does not report the repository's configuration as trusted
- **THEN** resolution carries no trust to its copy and its result is unchanged
- **AND** a refusal names `mise trust` as the next action where trust can select the locked install
