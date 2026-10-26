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

#### Scenario: An admitted command runs a host command

- **WHEN** an admitted command runs a host command such as `git` or `tar`
- **THEN** its PATH holds the locked tools ahead of the host's own command baseline, and nothing else from the caller's PATH
- **AND** on Windows that baseline holds the system command directories and the shell-free Git launcher, but no shell and not the current directory
