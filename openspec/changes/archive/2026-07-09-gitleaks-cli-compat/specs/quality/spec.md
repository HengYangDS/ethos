## MODIFIED Requirements

### Requirement: Release supply-chain evidence binds tools, secrets, SBOM, and attestation

ETHOS release-profile quality gates SHALL bind tool downloads, secret scanning,
transitive dependencies, and release attestation materials to current repository
truth.

#### Scenario: supply-chain evidence is emitted for release readiness

- **WHEN** release quality surfaces emit SBOM or release attestation evidence
- **THEN** the SBOM includes workspace packages and lockfile transitive packages
- **AND** the SBOM records the `uv.lock` digest and package layer counts
- **AND** release attestation includes SLSA materials for Git HEAD, evidence,
  `uv.lock`, and SBOM digest
- **AND** the gitleaks installer validates cached archives with pinned SHA-256
- **AND** the secrets gate scans both current tree and Git history
- **AND** the Git history scan invokes `gitleaks git` with the repository path as
  the command argument rather than the removed `--source` flag
