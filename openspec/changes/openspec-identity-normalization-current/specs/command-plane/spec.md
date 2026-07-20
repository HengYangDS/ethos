## MODIFIED Requirements

### Requirement: OpenSpec archive query uses logical Change IDs

ETHOS SHALL expose an explicit read-only archive query that accepts a date-free
lower-kebab logical OpenSpec Change ID beginning with a letter, and resolves
exactly one `YYYY-MM-DD-<logical-id>` archived carrier under
`openspec/changes/archive` without mutating historical archives. A terminal
`YYYYMMDD` segment is not part of a logical Change ID.

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

#### Scenario: Numeric or temporal logical IDs are rejected

- **WHEN** an archive query receives a numeric-leading ID, terminal-date ID,
  archive directory name, absent ID, or ambiguous logical ID
- **THEN** ETHOS SHALL reject it as an invalid logical Change ID
- **AND** it SHALL require the date-free logical ID rather than a compatibility
  alias, redirect, or fallback lookup.
