## ADDED Requirements

### Requirement: Native supply resolution leaves no host mise state

Resolving native tool supply SHALL run mise in safe mode over a disposable directory and SHALL keep mise's state in that directory. Resolution thus runs no repository task, hook or template and records nothing in the host's mise state. Provisioning into a disposable root SHALL keep mise's state in that root.

#### Scenario: A resolution completes

- **WHEN** ETHOS resolves a repository's declared version files, a locked tool or a locked environment
- **THEN** the host's mise state is unchanged and no repository task ran
- **AND** the resolved executables are those of the locked selection

### Requirement: Locked execution keeps native mise policy

The environment that ETHOS gives an admitted repository command SHALL expose the locked tools with configuration isolation, locked and offline selection, no automatic installation and no prompts. It SHALL NOT carry resolution's safe mode or disposable state, and a caller's explicit safe mode and state directory SHALL apply. Trust SHALL remain mise's decision: ETHOS SHALL NOT trust a configuration, edit a trust record or override a native refusal.

#### Scenario: An admitted command runs repository tasks

- **WHEN** an admitted command runs a repository task that runs another task through native mise
- **THEN** both tasks run with the locked tools

#### Scenario: The caller selected safe mode

- **WHEN** the caller's environment selects mise's safe mode
- **THEN** native mise still refuses to run repository tasks

#### Scenario: An untrusted configuration needs trust

- **WHEN** an admitted command reads an untrusted repository configuration that needs trust through a mise command that does not trust it
- **THEN** nothing in that configuration runs and ETHOS records no trust for it
