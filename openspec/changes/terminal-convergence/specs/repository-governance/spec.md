## MODIFIED Requirements

### Requirement: publication topology is declared, not inferred

The repository SHALL declare every publication peer explicitly and MAY declare
no remote peer for a local-only topology. The declaration
SHALL contain a unique peer ID, provider, Git remote, role, and capability set;
peer IDs, providers, and Git remotes SHALL each be unique. Publication,
admission, pre-push, and reconciliation SHALL consume only this collection and
SHALL NOT require an absent provider.

#### Scenario: publication is local only

- **WHEN** the peer collection is empty and both local commands are valid
- **THEN** topology and local publication readiness are valid with no remote observation or hosted claim

#### Scenario: GitLab is the only declared peer

- **WHEN** a repository declares one GitLab peer with repository and publication capabilities
- **THEN** topology and remote admission are valid without GitHub or a hosted CI surface

#### Scenario: GitHub is the only declared peer

- **WHEN** a repository declares one GitHub peer with repository and publication capabilities
- **THEN** topology and remote admission are valid without GitLab or a hosted CI surface

#### Scenario: both remote peers are declared

- **WHEN** a repository explicitly declares distinct GitLab and GitHub peers
- **THEN** both peers are independently observed without making either one the primary peer

#### Scenario: peer identity is ambiguous

- **WHEN** two peers reuse an ID, provider, or Git remote
- **THEN** topology fails closed before remote observation or mutation

#### Scenario: retired and current declarations coexist

- **WHEN** peer tables coexist with a fixed provider scalar
- **THEN** topology fails closed as an ambiguous declaration

### Requirement: hosted CI claims follow declared capabilities

A publication peer SHALL require a repository-relative CI surface only when it
declares the `ci_cd` capability. Omitting that capability SHALL NOT manufacture
a hosted-CI claim or block repository publication.

#### Scenario: repository-only peer has no CI

- **WHEN** a declared peer omits `ci_cd` and `ci_surface`
- **THEN** local verification remains required and hosted CI remains unclaimed
