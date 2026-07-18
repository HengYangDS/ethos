## ADDED Requirements

### Requirement: Release And Adoption Evidence Boundary

ETHOS SHALL record release and adoption readiness evidence without conflating
local readiness, remote Git reference state, hosted CI observation, or registry
publication.

#### Scenario: External adoption pilots are evidence-bounded

- **WHEN** ETHOS claims external adoption readiness
- **THEN** tracked evidence names at least generic, Python, and GitLab pilot
  repositories
- **AND** each successful pilot records adopt apply, status, report, playbooks,
  and proof-readiness outcomes
- **AND** conflict guards such as a non-empty existing `.gitlab-ci.yml` are
  recorded as protected-adopter outcomes rather than overwritten silently

#### Scenario: Release smoke remains local until published externally

- **WHEN** ETHOS reports release readiness
- **THEN** local artifact builds, installer or launcher smoke checks, and
  artifact digests may support local readiness
- **AND** remote ref alignment is recorded separately from hosted CI status
- **AND** hosted CI success or package registry publication is not claimed unless
  those external systems are observed directly
