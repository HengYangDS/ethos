## ADDED Requirements

### Requirement: Official OpenSpec goal metadata is lifecycle-compatible

ETHOS SHALL accept the official OpenSpec 1.6 `goal` field in active and archived
`.openspec.yaml` metadata while continuing to reject unrecognized metadata
keys.

#### Scenario: Official change creation supplies a goal

- **WHEN** an OpenSpec change metadata file contains `schema`, `created`, and
  an official `goal`
- **THEN** ETHOS metadata compatibility and archive closeout SHALL not report a
  metadata-key gap for `goal`
- **AND** an unknown key such as `owner` SHALL remain a required compatibility
  gap.
