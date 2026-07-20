## MODIFIED Requirements

### Requirement: Release Policy

ETHOS SHALL expose a release policy report covering version alignment, hosted
profile surfaces, protected branch/tag expectations, attestation formats,
publication topology, and the executable local verification/install owners
declared by that topology.

#### Scenario: Release policy is complete

- **WHEN** `ethos quality release-policy --json` runs in the ETHOS repository
- **THEN** the result reports no required gaps for release files, hosted profile
  templates, protected refs, version alignment, attestation formats,
  publication topology, and local command owners
- **AND** each declared local verification or installation command resolves to
  an executable regular file inside the governed repository.

#### Scenario: Phantom local owner blocks release readiness

- **WHEN** a declared local verification or installation command is absent,
  names a missing or non-regular file, or lacks an executable bit
- **THEN** release policy SHALL report a stable required gap for that field and
  path
- **AND** `ok` SHALL be false.

#### Scenario: Local owner cannot escape the repository

- **WHEN** a declared local command is absolute, contains a traversal that
  resolves outside the repository, or follows a link outside the repository
- **THEN** release policy SHALL report a path-escape required gap
- **AND** it SHALL NOT inspect or execute the outside target as a release owner.
