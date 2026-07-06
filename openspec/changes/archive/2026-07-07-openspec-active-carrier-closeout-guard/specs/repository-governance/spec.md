## ADDED Requirements

### Requirement: Active OpenSpec Carriers Do Not Survive Promotion

ETHOS SHALL block candidate and accepted-root repository states that retain
active OpenSpec change carriers under `openspec/changes/`.

#### Scenario: Work Lane may author active carrier

- **WHEN** a Work Lane contains an active OpenSpec change
- **THEN** repository audit may validate the carrier shape
- **AND** the active carrier does not by itself block Work Lane authoring.

#### Scenario: Protected roles reject active carrier residue

- **WHEN** the current branch role is `candidate` or `accepted_root`
- **AND** an active change exists under `openspec/changes/`
- **THEN** repository audit reports `openspec_active_change_unarchived:<change>:<role>`
- **AND** report, prove, land, and closeout cannot claim clean governance until
  the carrier is archived.
