## MODIFIED Requirements

### Requirement: Protected ref hooks bind semantic evaluation to promoted control

ETHOS SHALL keep the accepted checkout as the fail-closed shell-hook boundary
for every protected ref in an official closeout transaction. When that
transaction promotes a candidate head, it SHALL evaluate the semantic
ref-admission reducer using a clean linked checkout of the configured candidate
branch at that exact promoted head.

#### Scenario: candidate control implementation differs from accepted checkout

- **GIVEN** the accepted checkout contains an older control implementation
- **AND** the configured candidate checkout is clean, bound to the configured
  candidate branch, and resolves to the promoted candidate head
- **AND** the candidate changes admission or proof-policy behavior
- **WHEN** official accepted-root closeout advances the accepted ref
- **THEN** the protected hook SHALL run the candidate-tree semantic evaluator
  against the candidate head
- **AND** it SHALL bind runner source, candidate checkout, candidate head, and
  transition fields explicitly
- **AND** it SHALL not reject solely because accepted-old source would compute
  a different policy result.

#### Scenario: accepted-to-release mirror uses promoted candidate control

- **GIVEN** the candidate policy enables `release_mirror = "accepted_ff"`
- **AND** official closeout atomically advances accepted and configured release
  refs to the proven candidate head
- **AND** accepted-old ref-admission behavior differs from candidate control
- **WHEN** the reference-transaction hook evaluates the release-ref member
- **THEN** it SHALL use the same bound candidate semantic runner as the
  accepted-ref member
- **AND** it SHALL still require the release topology, proof, and exact
  one-shot closeout intent
- **AND** incumbent source SHALL not decide the release-ref member.

#### Scenario: candidate semantic runner cannot be bound

- **WHEN** the configured candidate checkout is missing, dirty, detached,
  stale, or its semantic runtime cannot be bound to that checkout
- **THEN** the protected hook SHALL reject the transition
- **AND** it SHALL not fall back to accepted-old semantic source.

#### Scenario: changed managed shell hook bootstraps an accepted-to-release mirror

- **GIVEN** the candidate policy enables `release_mirror = "accepted_ff"`
- **AND** the candidate changes the tracked `reference-transaction` shell hook
- **AND** the incumbent shell can admit the accepted transition only through the
  candidate semantic runner
- **WHEN** official closeout performs the hook deployment bootstrap
- **THEN** it SHALL advance the accepted ref through an ordinary exact-intent,
  proof-bound compare-and-swap
- **AND** it SHALL synchronize the accepted checkout before advancing the
  release mirror through the promoted shell hook
- **AND** it SHALL not use a direct ref update, hook disablement, or hook-path
  override
- **AND** it SHALL report incomplete release-mirror bootstrap residue rather
  than accepted closeout when the second transition cannot complete.
