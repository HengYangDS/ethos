## MODIFIED Requirements

### Requirement: Accepted closeout remains candidate-first and non-self-approving

ETHOS SHALL admit an accepted-branch advance only when it fast-forwards to the
live candidate head, carries candidate-head proof, and is an official closeout
identified by a one-shot transition marker. Candidate-tree semantic evaluation
shall determine the promoted tree's admission policy; the accepted checkout
shall retain the protected Git-hook and CAS boundary. When the declared policy
uses `release_mirror = "accepted_ff"`, the release-mirror ref is an additional
protected transition in the same atomic closeout and SHALL use that exact clean
candidate semantic evaluator as well. If the candidate replaces the tracked
reference-transaction hook, the official atomic closeout SHALL invoke Git with
the exact clean candidate hook directory for that single transaction; it SHALL
require that hook file to be present and executable and SHALL not mutate global
hook configuration or weaken raw Git admission. A closeout that does not
replace that tracked hook SHALL retain its configured-hook route.

#### Scenario: raw update-ref targets a proven candidate head

- **GIVEN** the candidate checkout is clean and has a complete proof for its
  live head
- **WHEN** a caller runs raw `git update-ref` to move the accepted branch to
  that head without official closeout intent
- **THEN** the accepted-ref hook SHALL reject the move
- **AND** candidate-tree evaluation SHALL not make the marker optional.

#### Scenario: Official accepted_ff closeout advances both protected refs

- **GIVEN** `dev` and `main` are atomically advanced by an official
  `accepted_ff` closeout to the live, proven candidate head
- **AND** the incumbent accepted checkout cannot run its hook reducer
- **WHEN** the armed reference-transaction hook prepares the transaction
- **THEN** it evaluates both transitions through the clean candidate runner
- **AND** it admits the transaction only when each exact closeout intent and
  substantive candidate/proof check passes
- **AND** `dev` and `main` reach the same candidate head atomically.

#### Scenario: Raw accepted or release-mirror move remains blocked

- **GIVEN** an `accepted_ff` repository has a proven live candidate head
- **WHEN** raw Git attempts to move `dev` or `main` without its exact
  closeout-intent marker
- **THEN** the armed hook blocks that transition
- **AND** no protected ref advances.

#### Scenario: Candidate hook replaces a legacy accepted hook

- **GIVEN** the accepted checkout has a legacy reference-transaction hook that
  rejects an accepted_ff release-mirror transition
- **AND** the clean candidate checkout at the proposed head contains the
  repaired executable hook
- **WHEN** official closeout performs its one atomic compare-and-swap
- **THEN** Git invokes that candidate hook directory only for the official
  transaction
- **AND** both protected refs are admitted or rejected together
- **AND** raw Git ref updates continue to use configured incumbent hook policy.

#### Scenario: Candidate hook is unavailable

- **GIVEN** the proposed candidate checkout lacks an executable
  reference-transaction hook
- **WHEN** official closeout is evaluated
- **THEN** ETHOS blocks before its CAS
- **AND** it does not run an unguarded transaction or silently select another
  hook directory.

#### Scenario: Rejected atomic update does not impersonate concurrency

- **GIVEN** atomic closeout update-ref returns an error and the accepted ref is
  still its captured old head
- **WHEN** ETHOS projects the closeout failure
- **THEN** it reports an atomic-update rejection with stderr
- **AND** it does not report accepted concurrent advancement.

#### Scenario: Independent release branch remains non-protected

- **GIVEN** the current policy declares an independent release branch
- **WHEN** that release ref changes outside an accepted_ff closeout
- **THEN** the hook does not require candidate-runner availability solely for
  that release ref
- **AND** existing non-protected admission behavior remains in force.
