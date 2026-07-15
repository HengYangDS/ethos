## ADDED Requirements

### Requirement: Three-Layer Peer-Complete Provider Topology

ETHOS SHALL model local verification and installation plus separate, complete
GitLab and GitHub repository and CI/CD planes. GitLab SHALL remain the
organizational primary publication authority.

#### Scenario: local validation is remote-independent

- **WHEN** a repository evaluates local verification or installation readiness
- **THEN** it SHALL not require GitLab or GitHub reachability
- **AND** it SHALL not claim remote publication or hosted CI success.

#### Scenario: GitLab is the organizational primary

- **WHEN** ETHOS projects publication readiness
- **THEN** the configured GitLab primary remote SHALL remain the organization
  publication authority
- **AND** a GitHub fact SHALL NOT satisfy a GitLab-primary publication claim or
  GitLab hosted-status claim.

#### Scenario: providers are peer complete planes

- **WHEN** a repository declares the three-layer peer-complete provider topology
- **THEN** its GitLab and GitHub provider profiles SHALL each declare the same
  repository, CI/CD, update, and distribution capability
- **AND** each provider profile SHALL expose CI, review-template, and
  issue-template surfaces
- **AND** GitLab SHALL remain the organizational primary publication authority.

#### Scenario: candidate integration remains local-only

- **WHEN** ETHOS projects the remote publication policy for either provider
- **THEN** it SHALL admit only `dev`, `main`, and `submit/*`
- **AND** it SHALL explicitly exclude `candidate/dev` from GitLab and GitHub
  remote transitions
- **AND** local pre-push admission SHALL reject an excluded or unaccepted
  destination before provider contact.

#### Scenario: provider observations remain distinct

- **WHEN** one configured provider is available and the other is unavailable
- **THEN** ETHOS MAY report that provider's independent complete plane
- **AND** it SHALL keep remote-publication and hosted-status claims false until
  the relevant provider transition or hosted observation is separately bound.
