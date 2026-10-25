## ADDED Requirements

### Requirement: Disposable mise copies carry only native trust

Resolution and provisioning SHALL carry to their disposable copy of the exact declared bytes only the trust that native mise, under the caller's own trust inputs, already reports for the repository's configuration, and only for that invocation. They SHALL write no trust record and SHALL NOT trust a configuration that native mise does not report as trusted. A resolution refused for an untrusted configuration SHALL name native `mise trust` as the next action.

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
- **AND** a refusal names `mise trust` as the next action

## MODIFIED Requirements

### Requirement: Locked execution keeps native mise policy

The environment that ETHOS gives an admitted repository command SHALL expose the locked tools with configuration isolation, locked and offline selection, no automatic installation and no prompts. It SHALL NOT carry resolution's safe mode, disposable state or trust, and a caller's explicit safe mode and state directory SHALL apply. Trust SHALL remain mise's decision: ETHOS SHALL NOT trust a configuration, edit a trust record or override a native refusal.

#### Scenario: An admitted command runs repository tasks

- **WHEN** an admitted command runs a repository task that runs another task through native mise
- **THEN** both tasks run with the locked tools

#### Scenario: The caller selected safe mode

- **WHEN** the caller's environment selects mise's safe mode
- **THEN** native mise still refuses to run repository tasks

#### Scenario: An untrusted configuration needs trust

- **WHEN** an admitted command reads an untrusted repository configuration that needs trust through a mise command that does not trust it
- **THEN** nothing in that configuration runs and ETHOS records no trust for it
