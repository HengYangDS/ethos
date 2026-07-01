## ADDED Requirements

### Requirement: Official OpenSpec Self-Governance
ETHOS SHALL keep `openspec/` as an official self-governance capability for
spec-driven planning and change records while preserving `ethos ...` as the only
public product command plane.

#### Scenario: OpenSpec is present but bounded
- **WHEN** an agent audits ETHOS product surfaces
- **THEN** `openspec/` is present as official governance record storage and is
  not treated as a replacement for ETHOS kernel, command output, schemas,
  tests, or current docs

#### Scenario: OpenSpec official validation is used
- **WHEN** ETHOS audits OpenSpec self-governance
- **THEN** it invokes the official OpenSpec CLI for status and strict validation
  instead of parsing OpenSpec records with ad hoc repository code

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

### Requirement: Commit And Hosted Verification Policy
ETHOS SHALL distinguish current local commit/signature status from GitLab
service-side verification status without requiring tracked historical alias
metadata.

#### Scenario: Current commit policy is audited
- **WHEN** `ethos quality commits --enforce-head --json` runs
- **THEN** the result reports local identity, subject, and signature gaps
  without inferring GitLab verification from local Git output
