## MODIFIED Requirements

### Requirement: Forge provider projections preserve ETHOS repository truth

ETHOS SHALL support GitHub and GitLab as hosted forge providers that project the
same Git-native repository governance contract without becoming repository truth.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** a repository enables both GitHub and GitLab provider profiles
- **THEN** provider templates SHALL invoke repository-owned gate scripts or
  `ethos ...` commands instead of duplicating policy inline
- **AND** provider YAML drift SHALL be checkable from tracked template sources
- **AND** provider-specific syntax checks SHALL NOT be treated as repository
  proof.

#### Scenario: Local provider emulation remains local evidence

- **WHEN** a GitHub or GitLab provider projection is emulated locally
- **THEN** the evidence SHALL name the local emulator evidence class
- **AND** it SHALL record the provider, template or projection path, command,
  start and end Git head, dirty state, return code, and changed-scope summary
- **AND** it SHALL record whether the Git head stayed stable for the emulator run
- **AND** normal emulator run modes SHALL refuse untracked files by default
  because provider materialization can omit them
- **AND** it SHALL explicitly state that hosted provider status was not claimed.
