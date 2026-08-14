## ADDED Requirements

### Requirement: Attestation record and query project one set contract

The public command plane SHALL expose one narrow record/query surface over the
Attestation set. Record SHALL issue from explicit canonical input or validate an
existing Attestation, then exact-CAS union it. Query SHALL filter the selected set
by exact semantic fields without creating selection, workflow, or task state.

#### Scenario: An input occurrence is recorded

- **WHEN** explicit source occurrence coordinates, predicate, subject, verifier,
  payload, relations, and bindings are valid
- **THEN** the command issues one canonical Attestation and adds it idempotently
- **AND** structured output returns set root and Attestation identity

#### Scenario: Unknown input is queried

- **WHEN** its payload or relation kind is not understood by an effect evaluator
- **THEN** query returns the preserved canonical value
- **AND** no command projection describes it as authoritative

### Requirement: Commitment rebind owns one destructive v2 bootstrap

The existing rebind family SHALL accept one explicit bootstrap plan that treats
the old v1 Lease tuple as opaque expected state and validates the exact new v2
carrier. The public result SHALL be structured and recoverable without manual
ref or SQLite edits.

#### Scenario: Bootstrap is interrupted

- **WHEN** execution stops at any ref, Lease, or Attestation boundary
- **THEN** recovery recognizes only the exact old tuple or exact v2 tuple
- **AND** returns one safe continuation without a traceback
