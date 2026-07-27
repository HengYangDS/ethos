## ADDED Requirements

### Requirement: Three-profile Homomorphism Proof
The release proof MUST execute the full lifecycle against a Python package, a Node/polyglot repository, and a docs/infra repository without imposing Python layout, OpenSpec, or the ETHOS self-profile physical grammar.

#### Scenario: Docs and infrastructure adopter is governed
- **WHEN** it declares native carriers, gates, branch roles, and release effects
- **THEN** the same lifecycle and verdict semantics complete without Python package assumptions

### Requirement: Lifecycle Concurrency Proof
Authority, lease, handoff, takeover, candidate CAS, retry, crash recovery, and replay invariants MUST be exercised by stateful property tests and a bounded formal transition model.

#### Scenario: A crash occurs after effect and before receipt return
- **WHEN** the same plan resumes from observed facts and attestations
- **THEN** it emits or recovers exactly one matching effect attestation and never repeats a conflicting mutation

### Requirement: Evidence-plane Isolation
Local, GitLab, and GitHub observations MUST remain separately identified and MUST NOT self-promote across authority planes.

#### Scenario: Local proof is complete but providers are unavailable
- **WHEN** all local gates pass at the terminal head
- **THEN** local proof is pass while both provider publication states remain unknown

### Requirement: Bounded Comparative Assurance Proof

Comparative assurance SHALL execute only through prove and emit a bounded
Attestation. It creates no command family, schema, root, or tracked evidence
plane.

#### Scenario: Parity gaps are checked

- **WHEN** ethos prove --gate comparative-assurance --json runs
- **THEN** the resulting Attestation reports the verifier, scope, input digests,
  verdict, and required gaps

## MODIFIED Requirements

### Requirement: Governance Lifecycle Fixtures
ETHOS SHALL provide reusable tests and fixtures for complete and malformed
ChangeContract, strict LaneLease, PlanIR, Attestation, and OpenSpec lifecycles.

#### Scenario: Complete lifecycle fixture passes
- **WHEN** tests load a complete governance lifecycle fixture
- **THEN** base-bound Lease admission, OpenSpec lifecycle review, proof
  Attestation validation, and guarded effect validation report no required gaps

#### Scenario: Malformed lifecycle fixture fails
- **WHEN** tests load a malformed governance lifecycle fixture
- **THEN** ETHOS reports specific required gaps for an unknown, expired, or
  missing Lease, a base ChangeContract digest mismatch, missing proof
  Attestation, or malformed OpenSpec carrier state

## REMOVED Requirements

### Requirement: Shadow Parity Evidence

**Reason**: A separate parity command and tracked evidence plane duplicate prove
and Attestation.

**Migration**: The baseline gap scenario moves to Bounded Comparative Assurance
Proof.

**Replacement**: Bounded Comparative Assurance Proof
