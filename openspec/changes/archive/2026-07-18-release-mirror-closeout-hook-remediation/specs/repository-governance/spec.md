## MODIFIED Requirements

### Requirement: Accepted closeout remains candidate-first and non-self-approving

ETHOS SHALL admit an accepted-branch advance only when it fast-forwards to the
live candidate head, carries candidate-head proof, and is an official closeout
identified by a one-shot transition marker. Candidate-tree semantic evaluation
shall determine the promoted tree's admission policy; the accepted checkout
shall retain the protected Git-hook and CAS boundary. When the declared policy
uses `release_mirror = "accepted_ff"`, the release-mirror ref is an additional
protected transition in the same atomic closeout and SHALL use that exact clean
candidate semantic evaluator as well.

#### Scenario: raw update-ref targets a proven candidate head

- **GIVEN** the candidate checkout is clean and has a complete proof for its
  live head
- **WHEN** a caller runs raw `git update-ref` to move the accepted branch to
  that head without official closeout intent
- **THEN** the accepted-ref hook SHALL reject the move
- **AND** candidate-tree semantic evaluation SHALL not make the marker optional.

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

#### Scenario: Independent release branch remains non-protected

- **GIVEN** the current policy declares an independent release branch
- **WHEN** that release ref changes outside an accepted_ff closeout
- **THEN** the hook does not require candidate-runner availability solely for
  that release ref
- **AND** existing non-protected admission behavior remains in force.
