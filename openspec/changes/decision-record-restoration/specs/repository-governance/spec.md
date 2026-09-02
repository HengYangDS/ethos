## ADDED Requirements

### Requirement: Minimal Decision Rationale Preservation

ETHOS SHALL retain a documentation decision record only when deleting it would
erase context, rejected alternatives, consequences, or a falsifiable revisit
condition not already carried by the current semantic owner. A decision record
SHALL explain why and SHALL NOT own current product meaning, mutation authority,
proof authority, workflow state, or task progress.

#### Scenario: Historical decision material is evaluated

- **WHEN** a removed decision subsystem contains rationale from several files
- **THEN** ETHOS SHALL retain only semantically distinct rationale
- **AND** overlapping records SHALL be merged
- **AND** a record fully absorbed by a current owner SHALL remain deleted.

#### Scenario: Decision rationale uses the minimum physical shape

- **WHEN** ETHOS retains more than one decision rationale
- **THEN** records SHALL use lowercase semantic filenames under
  `docs/decisions/`
- **AND** `docs/README.md` SHALL navigate them directly
- **AND** no decisions-local README, index, template, schema, registry,
  lifecycle directory, or runtime consumer SHALL be introduced solely for the
  records.

#### Scenario: Current authority is resolved

- **WHEN** a reader opens a decision record
- **THEN** the record SHALL identify the current semantic owner
- **AND** current behavior SHALL be determined by that owner rather than by the
  historical rationale.

### Requirement: Singular Documentation Entrypoint

ETHOS SHALL expose `docs/README.md` as its sole current documentation
entrypoint.

#### Scenario: Current documentation is traversed

- **WHEN** a current source, policy, or documentation carrier links to the
  documentation entrypoint
- **THEN** it SHALL link to `docs/README.md`
- **AND** `docs/index.md` SHALL be absent
- **AND** immutable historical evidence MAY retain the path observations that
  were true when it was recorded.

#### Scenario: An adopter uses the portable Docs Registry

- **WHEN** ETHOS audits an adopted repository
- **THEN** the adopter SHALL NOT be required to reproduce ETHOS's
  `docs/decisions/` directory or root documentation filename
- **AND** portable subject, role, state, and relation semantics SHALL remain the
  shared contract.
