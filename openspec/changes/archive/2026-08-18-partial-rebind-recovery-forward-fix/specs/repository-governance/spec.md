## ADDED Requirements

### Requirement: Commitment rebind partial effects recover through the original receipt

ETHOS SHALL recover a Commitment rebind whose exact Git CAS is durable while
the Lane Lease still matches the immutable receipt's old generation. Recovery
SHALL consume the original receipt, validate or reconstruct only its exact
plan-bound Git-effect evidence, advance only that exact Lease generation, and
persist the terminal rebind Attestation.

#### Scenario: Exact old-generation Lease is recovered after Git CAS

- **GIVEN** the receipt target ref and tree are current
- **AND** the Lease exactly matches the receipt's old generation
- **AND** the exact plan-bound Git-effect Attestation is selected
- **WHEN** the same public rebind command is retried
- **THEN** dry-run reports `ready_to_recover` without mutation
- **AND** apply advances the Lease once and persists the terminal Attestation

#### Scenario: Partial state reconstructs its missing Git-effect witness

- **GIVEN** the target ref is current while the Lease remains at the old generation
- **AND** the immutable receipt, target tree, index, and overlay are exact
- **AND** no Git-effect Attestation or ref intent remains from the failed apply
- **WHEN** the same public rebind command is retried
- **THEN** ETHOS reconstructs the original plan-bound intent without updating the ref
- **AND** persists the Git-effect Attestation before advancing the exact Lease generation

#### Scenario: Partial recovery coordinates drift

- **GIVEN** a receipt for an interrupted Commitment rebind
- **WHEN** its ref, tree, Lease generation, holder, digest, index, overlay, or plan differs
- **THEN** ETHOS rejects recovery before mutation
