## ADDED Requirements

### Requirement: Accepted Specification Reconciliation

Accepted specifications SHALL describe only current implemented behavior and
SHALL NOT gain authority from an archived Change, migrated checklist, or stale
historical projection.

#### Scenario: An accepted requirement has no current executable owner

- **WHEN** reconciliation cannot map an accepted requirement to current source,
  tests, schemas, or a currently admitted external verifier
- **THEN** the requirement is removed, narrowed, or reported as a model gap
- **AND** historical wording is not retained merely because it once appeared in
  an archived Change.

#### Scenario: A migrated successor has not been implemented

- **WHEN** an archived source task maps an obligation to a successor outcome
- **THEN** the archive proves only lossless migration of that obligation
- **AND** the successor remains incomplete until its own Change is implemented,
  proved, archived, landed, and retired.
