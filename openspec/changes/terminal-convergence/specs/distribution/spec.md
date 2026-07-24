## ADDED Requirements

### Requirement: Three Independent Delivery Planes
Local installation and validation MUST require no remote; GitLab and GitHub MUST each be independently capable of repository CI/CD, release, update, and distribution over the same immutable source and artifacts.

#### Scenario: GitLab is unavailable
- **WHEN** the terminal commit and artifacts have valid independent GitHub attestations
- **THEN** GitHub may serve updates and distribution without being described as GitLab proof

### Requirement: Cross-provider Artifact Identity
A release MUST bind the same immutable commit, signed tag, package versions, SBOM, provenance statement, and artifact digests on both providers.

#### Scenario: Provider artifact digests differ
- **WHEN** GitLab and GitHub publish non-identical bytes for the nominal release
- **THEN** publication remains blocked and neither provider result is promoted to complete release evidence

### Requirement: Single Terminal Remote Closeout
Intermediate campaign changes MUST use local closeout only; remote proposal, CI/CD, protected branch advancement, and release MUST occur once at the campaign terminal commit.

#### Scenario: A non-terminal campaign task passes locally
- **WHEN** later campaign tasks remain open
- **THEN** ETHOS records local proof and does not require or initiate remote publication
