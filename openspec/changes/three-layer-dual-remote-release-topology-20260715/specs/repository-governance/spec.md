## ADDED Requirements

### Requirement: Three-Layer Dual-Remote Publication Topology

ETHOS SHALL model local verification and installation, GitLab primary
publication, and GitHub mirror distribution as separate release roles.

#### Scenario: local validation is remote-independent

- **WHEN** a repository evaluates local verification or installation readiness
- **THEN** it SHALL not require GitLab or GitHub reachability
- **AND** it SHALL not claim remote publication or hosted CI success.

#### Scenario: GitLab is the organizational primary

- **WHEN** ETHOS projects publication readiness
- **THEN** the configured GitLab primary remote SHALL remain the organization
  publication authority
- **AND** a GitHub mirror SHALL NOT satisfy a GitLab-primary publication claim
  or a GitLab hosted-status claim.

#### Scenario: GitHub carries bounded fallback distribution

- **WHEN** the GitLab primary remote is unavailable and the configured GitHub
  mirror is available
- **THEN** the publication projection MAY name GitHub as available for update
  and distribution
- **AND** it SHALL keep `remote_publication_claimed=false`
- **AND** it SHALL preserve GitLab primary publication as deferred.
