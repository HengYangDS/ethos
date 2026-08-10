## MODIFIED Requirements

### Requirement: Declared publication peer topology

The repository SHALL declare every publication peer explicitly and MAY declare
no remote peer for a local-only topology. The declaration SHALL contain a
unique peer ID, provider, Git remote, role, and capability set; peer IDs,
providers, and Git remotes SHALL each be unique. Publication, admission,
pre-push, and reconciliation SHALL consume only this collection, SHALL NOT
require an absent provider, and SHALL keep every remote observation no-push
until a separately authorized publication effect.

#### Scenario: local-only publication remains valid

- **WHEN** `[publication]` declares valid local commands and no peers
- **THEN** `ethos publish` SHALL perform no remote observation
- **AND** local readiness MAY pass without claiming hosted CI or remote publication

#### Scenario: independent remote observations remain no-push

- **WHEN** `ethos publish` observes one or more declared peers
- **THEN** it SHALL expose each target separately
- **AND** `remote_push` SHALL remain `not_performed`
- **AND** hosted CI status SHALL remain unclaimed unless separately evidenced

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

### Requirement: Strict remote publication admission

The required `[publication]` declaration SHALL contain the two local commands
and a zero-or-more `peers` collection. Each peer SHALL have unique non-empty
`id`, `provider`, and `git_remote` values plus a role and capability set.
`ci_surface` SHALL be required only for `ci_cd`; omitting that capability SHALL
NOT manufacture a hosted-CI claim or block repository publication. Admission
SHALL permit only `dev`, `main`, and `proposal/*` to a named declared remote;
local branches remain excluded. `ethos publish` SHALL only observe declared
targets and reject positional arguments.

#### Scenario: explicit remote admission preserves local candidate isolation

- **WHEN** pre-push admission receives a named declared target and `candidate/dev`
- **THEN** it SHALL reject the destination before proof admission
- **AND** it SHALL emit `publication_candidate_branch_remote_forbidden:candidate/dev`

#### Scenario: non-canonical declaration fails closed

- **WHEN** an adopter omits `[publication]`, mixes retired provider scalars with peer records, or supplies an unknown declaration field
- **THEN** ETHOS SHALL reject publication topology admission
- **AND** it SHALL NOT infer `origin`, preserve a compatibility state, or bypass branch enforcement

#### Scenario: repository-only peer has no CI

- **WHEN** a declared peer omits `ci_cd` and `ci_surface`
- **THEN** local verification remains required and hosted CI remains unclaimed
