## MODIFIED Requirements

### Requirement: Provider-neutral Repository Audit Composition
ETHOS repository lifecycle semantics SHALL accept provider reports through
explicit proof-gate composition rather than importing provider execution
packages into the repository audit.

#### Scenario: Repository audit runs without a provider
- **WHEN** `ethos prove --gate repository-audit --json` runs
- **THEN** the repository audit evaluates repository-owned semantics without
  importing or executing provider-specific OpenSpec adapters

#### Scenario: Full proof composes official OpenSpec validation
- **WHEN** `ethos prove --full --execute --expect-head <head> --json` runs
- **THEN** the proof plan evaluates repository audit and the official OpenSpec
  gate as separate declared gates
- **AND** neither gate becomes a second lifecycle command plane

#### Scenario: Empty current scope does not rehydrate historic archive authority
- **GIVEN** proof resolution has no current changed paths and retains only a
  valid historic OpenSpec archive authority
- **WHEN** full proof compiles its TransitionPlan for the current HEAD
- **THEN** the plan does not carry that historic archive authority as a prior
  attestation
- **AND** the plan does not report `proof_archive_scope_stale` solely because
  historic authorized paths are absent from the empty current scope
- **AND** an applicable non-empty current scope retains strict archive-path
  validation.
