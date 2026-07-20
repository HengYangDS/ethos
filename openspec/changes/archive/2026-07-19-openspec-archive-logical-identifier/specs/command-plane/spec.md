## ADDED Requirements

### Requirement: OpenSpec archive query uses logical Change IDs
ETHOS SHALL expose an explicit read-only archive query that accepts a logical
OpenSpec Change ID and resolves exactly one dated archived carrier under
`openspec/changes/archive` without mutating historical archives.

#### Scenario: Logical archive ID resolves uniquely
- **WHEN** `ethos openspec --archive-id <logical-id> --json` receives a valid
  logical ID with exactly one matching `YYYY-MM-DD-<logical-id>` archive
- **THEN** it reports `state=resolved` and the relative archive carrier path
- **AND** it does not invoke an active Change status lookup or archive mutation

#### Scenario: Archive query fails closed
- **WHEN** an archive query receives an invalid logical ID, an archive directory
  name, no matching archive, or more than one matching archive
- **THEN** it reports a distinct required gap for that condition
- **AND** it does not choose an archive by date or mutate an archive

### Requirement: Active Change selection excludes archive directory names
ETHOS SHALL keep `ethos openspec --change` scoped to active logical Change IDs.

#### Scenario: Archive directory is passed to active selector
- **WHEN** `ethos openspec --change` receives the exact name of an archived
  `YYYY-MM-DD-<logical-id>` directory
- **THEN** it reports `openspec_active_change_identifier_is_archive_directory:<name>`
- **AND** it does not treat the archived carrier as an active Change
