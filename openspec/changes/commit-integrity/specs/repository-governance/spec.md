## MODIFIED Requirements

### Requirement: Commit And Hosted Verification Policy

One owner SHALL compile tracked commit policy for subject, signature and optional
author/committer constraints. Identity, cryptographic trust, transport and Forge
attribution SHALL remain distinct. Admission SHALL apply trusted prestate policy;
a candidate SHALL NOT waive its own integration obligations.

#### Scenario: Real signature verification

- **WHEN** a signed commit is required by the selected policy
- **THEN** admission verifies exact object bytes against the protected trust anchor
- **AND** a signature envelope with invalid cryptography is rejected

#### Scenario: Verification inputs remain current

- **WHEN** one or many exact objects are verified against native SSH trust
- **THEN** every object uses the same captured configuration, anchor and revocation material
- **AND** source trust changes before observation completes reject the result
- **AND** temporary verification material is removed on normal exit or reported failure

#### Scenario: Identity requirements are declared

- **WHEN** policy constrains author or committer identity
- **THEN** the same constraint is checked before commit and on integrated objects
- **AND** absent constraints add no generic-adopter identity restriction

#### Scenario: Candidate weakens signing policy

- **WHEN** a candidate disables signing required by the trusted integration base
- **THEN** its introduced range is still evaluated under that trusted requirement

#### Scenario: Malformed policy fails closed

- **WHEN** a present identity constraint has malformed or unknown fields
- **THEN** compilation returns a precise error rather than disabling admission

#### Scenario: Independent evidence planes

- **WHEN** CI verifies an existing commit
- **THEN** it invokes the common owner without inventing authors or signing keys
- **AND** local signature success does not claim Forge verification

#### Scenario: Current commit policy is audited

- **WHEN** repository audit or head-bound proof evaluates current commit policy
- **THEN** it reports the tracked declaration, local identity, subject, and
  signature facts through the same compiler used by mutation
- **AND** it does not infer tracked policy from mutable Git configuration or
  GitLab verification from local Git output.

#### Scenario: Identity allowlist fields have no policy meaning

- **WHEN** a present commit-policy table contains `identity_mode` or
  `allowed_identities`
- **THEN** compilation fails closed with the exact unknown fields
- **AND** ETHOS does not preserve them as permissions, trust anchors, or
  compatibility metadata.

#### Scenario: CI verifies but does not manufacture commit identity

- **WHEN** a native CI projection prepares Git for repository checks
- **THEN** it does not synthesize an author identity, signing key, or
  `commit.gpgsign` setting when the job creates no commit
- **AND** it verifies existing objects through the repository-owned gates
  without an embedded TOML parser or policy default.
