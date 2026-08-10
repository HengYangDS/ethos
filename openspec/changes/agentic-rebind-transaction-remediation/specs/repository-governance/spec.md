# Repository governance delta

## ADDED Requirements

### Requirement: Archive effect authorizes its exact transition paths

ETHOS SHALL treat a verified archive-effect attestation as the authority for
the exact paths changed by that official archive transition across status,
plan, prove, and land.

#### Scenario: Exact archive transition is congruent across readers

- **GIVEN** the official archive command moved one completed Change and emitted
  a valid attestation binding the resulting HEAD, Lease generation, carrier,
  and exact changed paths
- **WHEN** status, plan, prove, or land evaluates that post-archive generation
- **THEN** every attested path is attributed as authorized by the archive effect
- **AND** none is re-rejected merely because the archive namespace is outside
  the former active carrier glob
- **AND** all four surfaces select the same current-generation path set.

#### Scenario: Missing or tampered archive authority fails closed

- **WHEN** the archive attestation is absent, ambiguous, stale, or its path set
  does not match the committed archive effect
- **THEN** ETHOS does not project archive-effect authority
- **AND** it does not infer permission from an archive path or historical lane
  delta.

### Requirement: Invocation and editor bindings have distinct remediation

ETHOS SHALL distinguish a missing invocation actor, a different holder, and a
missing editor-root binding so each condition has one accurate public recovery
step.

#### Scenario: Invocation actor is absent

- **WHEN** a mutation requires the current Lease holder and `ETHOS_ACTOR` is
  empty
- **THEN** ETHOS reports `invocation_actor_missing` with the expected holder
- **AND** it does not misreport a different-holder conflict.

#### Scenario: Valid Lease lacks editor-root input

- **WHEN** the current holder has a valid Lease but required editor-root input
  is absent
- **THEN** ETHOS reports `editor_root_missing`
- **AND** the remediation binds or supplies the current Work Lane editor root
- **AND** it does not recommend starting another lane.
