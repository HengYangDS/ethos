## ADDED Requirements

### Requirement: Published release artifacts carry build provenance

The release publication SHALL attest every archive and wheel it publishes with a GitHub artifact
attestation of its own workflow run before it creates the release, so that no release exists
without them and a consumer can verify each published file's origin independently of ETHOS.

#### Scenario: A release is published

- **WHEN** the release run publishes the qualified archives and wheels of a signed tag
- **THEN** each of those files has a GitHub artifact attestation of that run
- **AND** the attestation runs before the release is created, so a failed attestation stops the
  publication

#### Scenario: Release provenance and ETHOS proof stay separate

- **WHEN** a consumer verifies a published archive with `gh attestation verify`
- **THEN** the result establishes the file's build origin only
- **AND** it neither replaces an ETHOS proof or release Attestation nor is replaced by one
