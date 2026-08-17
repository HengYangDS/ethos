## ADDED Requirements

### Requirement: Proof admission is operation-authority specific

ETHOS SHALL admit a proof only when it is applicable to one exact operation
query before validating mutable dependencies or resolving conflicts.

#### Scenario: Historical Work Lane proof is not applicable

- **GIVEN** one HEAD has a historical Work Lane proof and a current repository
  proof
- **WHEN** the Work Lane Lease generation is retired
- **AND** candidate acceptance queries the exact repository Commitment,
  `candidate.accept` operation, and required proof floor
- **THEN** ETHOS SHALL select the repository proof
- **AND** the historical proof SHALL remain queryable but SHALL NOT invalidate
  candidate acceptance.

#### Scenario: Applicable proof conflict fails closed

- **GIVEN** two current proofs applicable to the same exact query
- **WHEN** their exact bindings or assertions differ
- **THEN** ETHOS SHALL return `stale_binding` or `contradiction`
- **AND** SHALL NOT authorize an effect.

#### Scenario: Wrong authority cannot satisfy the query

- **WHEN** a proof has the wrong HEAD, repository Commitment, operation, scope,
  plane, boundary, or floor
- **THEN** ETHOS SHALL reject it with a specific query gap
- **AND** SHALL NOT infer authority from another proof or retired Lease.
