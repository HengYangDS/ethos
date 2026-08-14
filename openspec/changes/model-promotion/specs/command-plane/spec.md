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

The existing rebind family SHALL accept one explicit `v1-to-v2-bootstrap`
operation that treats the old v1 Lease tuple as opaque expected state, privately
binds the old repository carrier bytes and stable identity, validates both exact
new v2 carriers, and creates the signed dangling target commit from the exact
staged index. The public result SHALL be structured and recoverable without
manual commit-tree, ref, or SQLite edits. Normal readers SHALL support v2 only.

#### Scenario: Bootstrap target is derived

- **WHEN** the staged index contains one valid v2 lane Commitment and one valid
  v2 repository Commitment over an exact current v1 generation
- **THEN** derive emits a receipt binding both old/new carrier byte digests,
  semantic digests, target commit/tree, index, overlay, actor, and Lease successor
- **AND** the private v1 decoder is not callable by status, plan, prewrite, or
  ordinary mutation

#### Scenario: Bootstrap is interrupted

- **WHEN** execution stops at any ref, Lease, or Attestation boundary
- **THEN** recovery recognizes only the exact old tuple or exact v2 tuple
- **AND** re-observes branch, Lease, and sole Attestation set before returning
  one safe continuation without a traceback
