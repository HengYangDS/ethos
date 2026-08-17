## ADDED Requirements

### Requirement: Accepted publication selects repository proof authority

ETHOS SHALL select proof for publication by the exact repository Commitment at
the accepted HEAD before evaluating Lease generations or proof conflicts.

#### Scenario: Retired Work Lane proof is inapplicable

- **GIVEN** the accepted HEAD has a current repository proof and a historical
  Work Lane proof whose Lease has been retired
- **WHEN** ETHOS evaluates accepted publication
- **THEN** ETHOS SHALL select the repository proof
- **AND** SHALL NOT let the historical Lease generation veto publication.

#### Scenario: Applicable authority conflict fails closed

- **GIVEN** multiple proofs match the selected repository Commitment
- **WHEN** their current bindings or assertions conflict
- **THEN** ETHOS SHALL return the typed conflict
- **AND** SHALL NOT authorize publication.

#### Scenario: Wrong repository authority is rejected

- **WHEN** no proof matches the accepted HEAD and repository Commitment
- **THEN** ETHOS SHALL reject publication
- **AND** SHALL NOT infer authority from a Change-bound or Work-Lane-bound proof.
