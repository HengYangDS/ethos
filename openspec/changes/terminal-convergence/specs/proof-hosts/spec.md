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
