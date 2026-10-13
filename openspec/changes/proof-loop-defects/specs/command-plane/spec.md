## ADDED Requirements

### Requirement: Archive validation failures carry the native issues

When official strict validation rejects the archive postimage, `ethos lane
archive-change` SHALL report each blocking native issue of every rejected item
as a diagnostic with its item, severity, path and message, so the failure is
diagnosable without repeating the archive.

#### Scenario: Merged canonical spec fails strict validation

- **WHEN** the archive merge leaves a canonical spec that strict validation
  rejects
- **THEN** the result blocks with `openspec_validation_failed:spec:<capability>`
  and compensates the archive effect as before
- **AND** its diagnostics name the rejected item and the native issue level,
  path and message
- **AND** the repair continuation and required gaps are unchanged.

#### Scenario: Validation output is unreadable

- **WHEN** the official validation output cannot be read
- **THEN** the result carries no invented diagnostics and keeps its existing
  unreadable gap.
