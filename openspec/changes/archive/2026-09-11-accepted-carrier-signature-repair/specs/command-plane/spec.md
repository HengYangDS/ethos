## ADDED Requirements

### Requirement: Accepted signature repair command

ETHOS SHALL expose a public, bounded repair for one exact unsigned accepted
commit. Readiness SHALL have no Git-object, ref or worktree mutation. Explicitly
authorized application SHALL create a trusted replacement, apply selected local
effects, and report completed, blocked, unknown or recoverable outcomes.

#### Scenario: Readiness has no signing effect

- **WHEN** an operator requests signature-repair readiness for an exact accepted head
- **THEN** ETHOS reports current prerequisites and the authorized apply action
- **AND** it does not create a replacement object or move refs or worktrees

#### Scenario: Application requires authorization

- **WHEN** repair application lacks explicit authorization or has stale coordinates
- **THEN** it rejects the request before creating a replacement object
- **AND** it identifies the failed boundary and one fresh next action

#### Scenario: Successful repair requires new proof

- **WHEN** the selected local repair effects finish and their postconditions hold
- **THEN** the result identifies the replacement commit and exact reproof command
- **AND** it does not claim proof, runtime activation or remote publication

#### Scenario: Recovery observes instead of repeating effects

- **WHEN** a signing or ref effect has completed but its acknowledgement was lost
- **THEN** recovery uses durable result evidence and current Git observations
- **AND** it does not create another replacement or repeat completed effects
- **AND** missing evidence remains unknown rather than implying completion
