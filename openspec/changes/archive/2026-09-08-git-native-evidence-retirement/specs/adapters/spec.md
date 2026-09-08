## MODIFIED Requirements

### Requirement: Non-authoritative Attestation stores are not current readers

The Git-native set selected by `refs/ethos/attestations-set` SHALL be the sole
current Attestation carrier. Git-common staging or caches SHALL NOT select
current proof. Historical Claim and Chronicle bytes SHALL remain retrievable
from Git history without requiring copies in the current workspace.

#### Scenario: A stale local Attestation exists

- **WHEN** a record is absent from the selected Git set
- **THEN** current readers and effects ignore it as proof
- **AND** neither its location nor a profile evidence-root declaration promotes it.

#### Scenario: The worktree has no evidence directory

- **WHEN** a valid Attestation is recorded or selected
- **THEN** the existing Git-native set validates and returns it
- **AND** the operation leaves the worktree index and files unchanged.
