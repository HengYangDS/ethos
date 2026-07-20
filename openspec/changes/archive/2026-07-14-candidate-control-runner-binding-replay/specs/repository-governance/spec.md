## ADDED Requirements

### Requirement: Accepted closeout remains candidate-first and non-self-approving

ETHOS SHALL admit an accepted-branch advance only when it fast-forwards to the
live candidate head, carries candidate-head proof, and is an official closeout
identified by a one-shot transition marker. Candidate-tree semantic evaluation
shall determine the promoted tree's admission policy; the accepted checkout
shall retain the protected Git-hook and CAS boundary.

#### Scenario: raw update-ref targets a proven candidate head

- **GIVEN** the candidate checkout is clean and has a complete proof for its
  live head
- **WHEN** a caller runs raw `git update-ref` to move the accepted branch to
  that head without official closeout intent
- **THEN** the accepted-ref hook SHALL reject the move
- **AND** candidate-tree semantic evaluation SHALL not make the marker optional.
