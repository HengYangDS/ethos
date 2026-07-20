## ADDED Requirements

### Requirement: Semantic attestation is receipt-bound and non-authorizing

ETHOS SHALL admit `semantic_attested` only when a typed candidate-external
receipt binds the exact claim, dated evidence digest, semantic promotion scope,
and current HEAD. The receipt SHALL record an independent reviewer role, basis,
allow verdict, validity interval, canonical payload digest, and
`mints_authority = false`.

#### Scenario: Attestation is absent or mismatched

- **WHEN** the claim-side declaration or external receipt is missing,
  malformed, stale, repository-local, or does not match a bound fact
- **THEN** ETHOS SHALL fail the claim closed with a machine-readable gap

#### Scenario: Digest-only claim remains portable

- **WHEN** a claim declares `digest_only`
- **THEN** ETHOS SHALL not require or inspect a semantic receipt directory,
  account, daemon, credential, network operation, or dedicated local account

#### Scenario: Semantic attestation has a current semantic scope

- **WHEN** a claim declares `semantic_attested`
- **THEN** its evidence freshness mode SHALL be `semantic_scope`
- **AND** its receipt scope and HEAD bindings SHALL match that current scope
