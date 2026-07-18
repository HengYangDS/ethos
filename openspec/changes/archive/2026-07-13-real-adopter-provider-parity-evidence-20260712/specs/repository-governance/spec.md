## ADDED Requirements

### Requirement: External-adopter profile evidence has a bounded durable record

ETHOS SHALL record a completed local external-adopter profile exercise through
an active claim and dated Chronicle that bind the observed product revision,
adopter revision, profile outcomes, and raw-bundle digest without promoting
host-local raw material or provider state into repository truth.

#### Scenario: Local profile evidence is promoted

- **WHEN** an isolated external-adopter exercise completes for one or more
  adoption profiles
- **THEN** its claim SHALL bind a dated Chronicle and a SHA-256 identity for the
  host-local raw bundle
- **AND** the Chronicle SHALL record each profile's bounded outcome and
  protected-surface preservation assertion
- **AND** it SHALL state whether remote publication was performed.

#### Scenario: Digest-bound evidence is reviewed

- **WHEN** a claim uses digest-only verification for external-adopter profile
  evidence
- **THEN** it SHALL NOT claim semantic correctness, hosted-provider execution,
  provider authority, or independent review
- **AND** it SHALL NOT require a named local account, credential, key, daemon,
  or network service for adopters that do not opt into one.
