## ADDED Requirements

### Requirement: A later Lease generation supersedes a lane's earlier proofs

Among current proofs of one HEAD that record a Work Lane's Lease generation, a proof whose
generation for that lane is lower than another valid proof's SHALL be superseded and SHALL NOT take
part in the binding or contradiction comparison. Proofs of one generation that differ in verifier or
claim SHALL remain contradictory.

#### Scenario: A handed-off lane lands on its new holder's proof

- **GIVEN** one HEAD proved under a lane's Lease generation 1 by its first holder and under
  generation 2 by the holder it was handed to
- **WHEN** a repository transition selects the proof
- **THEN** the generation 2 proof is selected and no contradiction is reported

#### Scenario: Verifiers of one generation still contradict

- **WHEN** two proofs of one HEAD record the same Lease generation and differ in verifier
- **THEN** the repository transition still reports `contradiction`
