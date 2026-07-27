## ADDED Requirements

### Requirement: Three Independent Delivery Planes
Local installation and validation MUST require no remote; GitLab and GitHub MUST each be independently capable of repository CI/CD, release, update, and distribution over the same immutable source and artifacts.

#### Scenario: GitLab is unavailable
- **WHEN** the terminal commit and artifacts have valid independent GitHub attestations
- **THEN** GitHub may serve updates and distribution without being described as GitLab proof

#### Scenario: A provider workflow is replayed locally
- **WHEN** a local runner executes the GitLab or GitHub workflow projection
- **THEN** it MAY issue `Attestation(kind = "proof")` bound to the local runner,
  provider-template digest, exact source head, and produced artifact digests
- **AND** the attestation identifies its plane as local provider replay
- **AND** it MUST NOT use `kind = "external-assurance"`, satisfy the provider's
  observation or publication state, or be described as hosted CI evidence

### Requirement: Cross-provider Artifact Identity
A release MUST bind the same immutable commit, signed tag, package versions, SBOM, provenance statement, and artifact digests on both providers.

#### Scenario: Provider artifact digests differ
- **WHEN** GitLab and GitHub publish non-identical bytes for the nominal release
- **THEN** publication remains blocked and neither provider result is promoted to complete release evidence

### Requirement: Single Terminal Remote Closeout
Intermediate ChangeContracts in one declared convergence program MUST use local
closeout only. Remote proposal, CI/CD, protected branch advancement, and release
MUST occur once at the commit admitted by the derived terminal program
predicate.

#### Scenario: A non-terminal program member passes locally
- **WHEN** another required member contract remains `block` or `unknown`
- **THEN** ETHOS records local proof and does not require or initiate remote publication
