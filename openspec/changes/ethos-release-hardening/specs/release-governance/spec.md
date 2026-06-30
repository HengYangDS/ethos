## ADDED Requirements

### Requirement: Release Policy
ETHOS SHALL expose a release policy report covering version alignment, GitLab
surfaces, protected branch/tag expectations, and attestation formats.

#### Scenario: Release policy is complete
- **WHEN** `ethos quality release-policy --json` runs in the ETHOS repository
- **THEN** the result reports no required gaps for release files, GitLab
  templates, protected refs, version alignment, and attestation formats

### Requirement: Release Attestation
ETHOS SHALL emit deterministic release attestation and SBOM projections without
publishing them as independent truth.

#### Scenario: Attestation is generated
- **WHEN** `ethos quality release-attestation --json` runs
- **THEN** the result includes an in-toto-shaped statement with SLSA-style
  builder facts and an SPDX-lite SBOM projection derived from repository
  metadata

### Requirement: History Identity Audit
ETHOS SHALL distinguish raw Git identity/signature status from GitLab
service-side verification status.

#### Scenario: History identity is audited
- **WHEN** `ethos quality history-identity --json` runs
- **THEN** the result reports raw metadata mismatches and unsigned commits as
  explicit release gaps instead of inferring GitLab verification from local Git
  output
