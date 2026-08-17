## ADDED Requirements

### Requirement: Candidate proof admission selects repository authority

ETHOS SHALL select the candidate HEAD's exact repository Commitment before
validating mutable dependencies or resolving conflicts.

#### Scenario: Historical Work Lane proof is not applicable

- **GIVEN** one HEAD has a historical Work Lane proof and a current repository
  proof
- **WHEN** candidate acceptance supplies the exact repository Commitment
- **THEN** ETHOS SHALL select the repository proof
- **AND** the historical proof SHALL remain queryable but SHALL NOT invalidate
  candidate acceptance.

#### Scenario: Applicable proof conflict fails closed

- **GIVEN** two current proofs bound to the selected authority
- **WHEN** their exact bindings or assertions differ
- **THEN** ETHOS SHALL return `stale_binding` or `contradiction`
- **AND** SHALL NOT authorize an effect.

#### Scenario: Wrong authority cannot satisfy candidate acceptance

- **WHEN** a proof has the wrong HEAD or repository Commitment
- **THEN** ETHOS SHALL reject it with a specific authority gap
- **AND** SHALL NOT infer authority from another proof.
