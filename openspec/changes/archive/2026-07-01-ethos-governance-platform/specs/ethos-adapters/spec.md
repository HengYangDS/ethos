## ADDED Requirements

### Requirement: Authorized Mutation
ETHOS SHALL block apply-mode land and publish unless authorization and expected
HEAD binding are explicit.

#### Scenario: Apply mode is requested
- **WHEN** `ethos land --apply` or `ethos publish --apply` runs
- **THEN** ETHOS requires explicit authorization and expected HEAD before any
  mutation can proceed

### Requirement: Evidence Locality
ETHOS SHALL keep local runtime state separate from durable evidence.

#### Scenario: Evidence is emitted
- **WHEN** ETHOS creates proof evidence
- **THEN** the evidence is HEAD-bound, digest-addressed, and separate from
  ignored local runtime state
