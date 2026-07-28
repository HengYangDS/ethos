## MODIFIED Requirements

### Requirement: Proof Separation
Local, GitLab, GitHub, and publication assurance planes SHALL be independent Attestation subjects; success in one plane SHALL not claim another.

#### Scenario: Conformance package is inspected
- **WHEN** tests inspect `proof-hosts`
- **THEN** it contains proof fixtures and sample helpers rather than runtime
  command semantics

#### Scenario: GitLab is unavailable
- **WHEN** local proof succeeds and GitLab cannot be observed
- **THEN** local assurance is current only for its plane and GitLab remains unknown

### Requirement: Product Migration Closure Proof
Terminal proof SHALL bind exact inputs, verifier, policy, and immutable tree identity so it is reproducible without replaying a historical workflow.

#### Scenario: Closure proof runs
- **WHEN** product migration closure is verified
- **THEN** unit and architecture tests pass
- **AND** all Python packages build wheel and sdist locally
- **AND** npm launcher smoke and dry-run pack pass without publishing
- **AND** OpenSpec validation and ETHOS proof report no required gaps

#### Scenario: the tree changes after proof
- **WHEN** the tree no longer matches the proof binding
- **THEN** the proof is stale and cannot authorize a later effect
