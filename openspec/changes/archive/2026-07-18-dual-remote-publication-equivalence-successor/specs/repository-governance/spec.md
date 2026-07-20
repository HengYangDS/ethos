## MODIFIED Requirements

### Requirement: Forge provider projections preserve ETHOS repository truth

ETHOS SHALL support GitHub and GitLab as hosted forge providers that project the
same repository governance contract without changing `status -> plan -> prove ->
land -> publish` semantics. GitLab and GitHub SHALL be independent remote planes
with equal `repository`, `ci_cd`, and `publication` capabilities; their distinct
organization-collaboration and public-distribution roles SHALL NOT create
precedence, failover, or replacement semantics. Provider CI SHALL accept only
`dev`, `main`, and `submit/*`; the local-only `candidate/dev` and every `work/*`
branch SHALL be excluded.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `submit/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local candidate is excluded from hosted providers

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `submit/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local provider emulation remains local evidence

- **WHEN** a GitHub or GitLab provider projection is emulated locally
- **THEN** the evidence SHALL name the local emulator evidence class
- **AND** it SHALL record the provider, template or projection path, command,
  start and end Git head, dirty state, return code, and changed-scope summary
- **AND** it SHALL record whether the Git head stayed stable for the emulator run
- **AND** observation modes such as `doctor`, `list`, and `dry-run` MAY report a
  missing optional emulator binary as bounded local evidence with
  `tool_available=false` without claiming hosted provider status
- **AND** materializing emulator run modes SHALL fail closed when the required
  emulator binary is unavailable
- **AND** normal emulator run modes SHALL refuse untracked files by default
  because provider materialization can omit them
- **AND** it SHALL explicitly state that hosted provider status was not claimed.
