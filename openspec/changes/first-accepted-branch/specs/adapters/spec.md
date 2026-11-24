## ADDED Requirements

### Requirement: Hooks read an absent accepted branch's creation first

For a move of the accepted branch from a zero old value that no recorded effect
has prepared, the accepted-ref hook SHALL read whether the requirement "An
absent accepted branch is created at the release head" admits it before it asks
for public closeout's prepared accepted-head decision.

#### Scenario: A zero old value is read before the closeout decision

- **GIVEN** a move of the accepted branch whose transaction reports a zero old value
- **AND** no recorded effect has prepared it
- **WHEN** the accepted-ref hook evaluates the move
- **THEN** it SHALL read whether the requirement "An absent accepted branch is created at the
  release head" admits the move
- **AND** it SHALL ask for public closeout's prepared accepted-head decision only when that
  requirement does not admit it.

## MODIFIED Requirements

### Requirement: Protected ref hooks bind semantic evaluation to promoted control

ETHOS SHALL retain the accepted checkout as the fail-closed shell-hook boundary.
For candidate promotion, semantic ref admission SHALL run in a clean linked
checkout of the configured candidate at the exact promoted HEAD. Hooks SHALL
consume public closeout's prepared accepted-head decision, not reconstruct proof
or topology or require protected refs to equal the promoted object already,
except as the requirement "Hooks read an absent accepted branch's creation
first" states.

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
- **AND** it SHALL consume the same prepared ref intent and proof decision as
  closeout
- **AND** it SHALL not reject solely because accepted-old source would compute
  a different policy result.

#### Scenario: candidate semantic runner cannot be bound

- **GIVEN** a move of the accepted ref, or of the release branch that mirrors
  it, that no recorded effect has prepared and that the requirement "An absent
  accepted branch is created at the release head" does not admit
- **WHEN** the configured candidate checkout is missing, dirty, detached,
  stale, or its semantic runtime cannot be bound to that checkout
- **THEN** the accepted-ref hook SHALL reject the transition
- **AND** it SHALL not fall back to accepted-old semantic source
- **AND** it SHALL project the complete public closeout command required to
  repair or retry the exact transition.

#### Scenario: changed managed shell hook bootstraps an accepted-to-release mirror

- **GIVEN** the candidate `.ethos/release.toml` declares `[release] mirror = "accepted_ff"`
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

#### Scenario: an exact protected object is pushed after local closeout

- **GIVEN** public closeout admitted and post-observed an exact signed candidate
  object through its prepared ref intent
- **WHEN** pre-push evaluates that same object for the declared protected role
- **THEN** the hook SHALL consume the admitted object and proof identity
- **AND** it SHALL not demand an additional hook-local role transition or a
  circular local-ref equality condition.
