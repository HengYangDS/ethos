## MODIFIED Requirements

### Requirement: Forge provider projections preserve ETHOS repository truth

GitHub and GitLab SHALL independently project the same `status -> plan -> prove
-> land -> publish` contract. Each has equal `repository`, `ci_cd`, and
`publication` capability; differing collaboration/distribution roles create no
precedence, failover, or replacement. Hosted CI accepts only `dev`, `main`, and
`proposal/*`; `candidate/dev` and `work/*` remain local.

#### Scenario: Dual provider templates mirror one gate contract

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `proposal/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local candidate is excluded from hosted providers

- **WHEN** the provider templates and projections are inspected
- **THEN** GitHub and GitLab SHALL include `dev`, `main`, and `proposal/*`
- **AND** neither SHALL include `candidate/dev`
- **AND** each SHALL invoke repository-owned gate scripts or `ethos ...`
  command surfaces rather than duplicating policy inline.

#### Scenario: Local provider emulation remains local evidence

- **WHEN** a contributor runs a GitHub or GitLab projection through a local emulator
- **THEN** its output stays a local observation that ETHOS neither records nor reads
- **AND** no proof, landing or hosted observation treats it as hosted provider status
