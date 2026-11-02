## MODIFIED Requirements

### Requirement: Archive validation failures carry the native issues

When official strict validation rejects the archive postimage, `ethos lane
archive-change` SHALL report each blocking native issue of every rejected item
as a diagnostic with its item, severity, path and message, so the failure is
diagnosable without repeating the archive. Its preview SHALL simulate the
archive and validate the merged specs strictly before it reports readiness.

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

#### Scenario: Preview refuses an archive that validation would reject

- **WHEN** the archive merge of the selected Change would leave a requirement
  that strict validation rejects
- **THEN** the preview blocks with the gap the proof's archive readiness
  reports, `openspec_archived_requirement_invalid:<change>:<capability>:<requirement>`
- **AND** it makes no archive effect.
