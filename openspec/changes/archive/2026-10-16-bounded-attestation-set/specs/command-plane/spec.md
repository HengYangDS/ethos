## MODIFIED Requirements

### Requirement: Attestation record and query project one set contract

The public command plane SHALL expose one narrow record, query and release surface over the
Attestation set. Record SHALL issue from explicit canonical input or validate an existing
Attestation, store its declared custody evidence, then exact-CAS union it. Query SHALL filter the
selected set by exact semantic fields without creating selection, workflow, or task state. Release
SHALL remove one open-predicate member by exact CAS.

#### Scenario: An input occurrence is recorded

- **WHEN** explicit source occurrence coordinates, predicate, subject, verifier, payload, relations,
  and bindings are valid
- **THEN** the command issues one canonical Attestation and adds it idempotently
- **AND** structured output returns set root and Attestation identity

#### Scenario: Unknown input is queried

- **WHEN** its payload or relation kind is not understood by an effect evaluator
- **THEN** query returns the preserved canonical value
- **AND** no command projection describes it as authoritative

#### Scenario: An oversized input is recorded

- **WHEN** the canonical input exceeds the member size bound
- **THEN** record refuses it with `attestation_member_too_large`
- **AND** names custody evidence as the carrier for its bytes

#### Scenario: An open-predicate member is released

- **WHEN** its verifier, or an actor that names reviewed content and a reason, applies release
- **THEN** the member leaves the selected set and its unbound custody bytes are deleted
- **AND** structured output returns the previous and the new set root

#### Scenario: Release is not admitted

- **WHEN** another actor omits reviewed content or a reason, or the member has a product lifetime
- **THEN** release refuses without changing the set or custody
