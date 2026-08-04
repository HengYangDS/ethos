## MODIFIED Requirements

### Requirement: Proof Separation
Local, GitLab, GitHub, publication, and records assurance planes SHALL be
independent Attestation subjects; success, evidence, or receipts in one plane
SHALL NOT claim another. GitLab and GitHub SHALL each be a complete hosted CI/CD
plane rather than a mirror, fallback, or proxy for the other.

#### Scenario: Conformance package is inspected
- **WHEN** tests inspect `proof-hosts`
- **THEN** it contains proof fixtures and sample helpers rather than runtime
  command semantics

#### Scenario: An assurance plane is unavailable
- **WHEN** any required plane is unavailable, stale, incomplete, or failed
- **THEN** that plane remains `unknown` or `block`
- **AND** local proof, the other provider, local provider emulation, publication
  receipts, hosted observations, and record verification cannot substitute for it
- **AND** record verification proves immutable package integrity only, while a
  publication receipt proves only the exact remote effect it observed
- **AND** local `act` or GitLab pipeline emulation remains local projection
  evidence and cannot satisfy either hosted provider subject

### Requirement: Product Migration Closure Proof
Terminal proof SHALL bind exact inputs, verifier, policy, and immutable tree
identity so it is reproducible without replaying a historical workflow. Closure
SHALL combine one HEAD-bound full local proof, the portable conformance kit over
three adopter classes, and bounded property, formal-model, and mutation proof.
Every proof, artifact, record package, hosted observation, and publication
receipt SHALL bind the same one terminal HEAD.

#### Scenario: Closure proof runs
- **WHEN** `ethos prove --execute --full --expect-head <terminal-head> --json`
  verifies product migration closure
- **THEN** unit and architecture tests pass at that exact head
- **AND** all Python packages build wheel and sdist locally
- **AND** npm launcher smoke and dry-run pack pass without publishing
- **AND** OpenSpec validation and ETHOS proof report no required gaps
- **AND** the portable conformance kit proves Python package, Node/polyglot, and
  docs/infra adopters through the same kernel relation and verdict semantics
- **AND** CLI, Python SDK, subprocess JSON, and any admitted protocol adapter
  preserve permissions, deterministic serialization, offline behavior, profile
  isolation, native carrier choice, and clean uninstall

#### Scenario: the tree changes after proof
- **WHEN** the tree no longer matches the proof binding
- **THEN** the proof is stale and cannot authorize a later effect

#### Scenario: lifecycle and race invariants are proved
- **WHEN** terminal lifecycle proof executes
- **THEN** stateful property tests exercise lease, handoff, takeover, candidate
  CAS, retirement, and crash-recovery transitions
- **AND** a bounded formal transition model checks safety and progress invariants
- **AND** mutation proof covers critical pure reducers, authority resolution,
  exact-CAS effects, and proof binding, with surviving in-scope mutants reported
  as required gaps
- **AND** an external model checker is admitted only when the native model cannot
  express or falsify one named invariant
- **AND** the result claims no correctness or completeness beyond the exact
  modeled state space, mutation scope, inputs, and verifier
