## MODIFIED Requirements

### Requirement: Official OpenSpec Lifecycle Adapter

ETHOS SHALL compose official OpenSpec CLI output with ETHOS lifecycle carrier
review and SHALL preflight an active change's archiveability through an isolated
official archive projection before proof, land, or accepted-root closeout.

#### Scenario: Archive closeout gaps block land and closeout

- **GIVEN** official OpenSpec list status has no completed active changes
- **AND** an archived change is missing archive metadata or has incomplete tasks
- **WHEN** ETHOS evaluates OpenSpec lifecycle closeout for land or accepted-root
  closeout
- **THEN** ETHOS reports the archive issue as a required gap
- **AND** land or closeout remains blocked until archive state is repaired.

#### Scenario: Active change fails official archive simulation

- **GIVEN** an active change is syntactically valid but the configured official
  OpenSpec archive command would reject its delta against the current canonical
  specs
- **WHEN** ETHOS evaluates OpenSpec lifecycle for the change
- **THEN** ETHOS runs the official archive only in a disposable workspace copy
- **AND** returns the official diagnostic code, message, and fix under the
  change's `archive_preflight` data
- **AND** reports a change-scoped required gap
- **AND** proof, land, and accepted-root closeout remain blocked
- **AND** the source OpenSpec workspace remains unchanged.

#### Scenario: Active change passes official archive simulation

- **GIVEN** an active change's official archive simulation succeeds
- **WHEN** ETHOS evaluates OpenSpec lifecycle for the change
- **THEN** lifecycle records a successful isolated preflight
- **AND** it does not archive the source change, complete tasks, or mint
  authority
- **AND** a later source change requires lifecycle to evaluate archiveability
  again.
