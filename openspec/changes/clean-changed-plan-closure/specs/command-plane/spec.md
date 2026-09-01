## ADDED Requirements

### Requirement: Empty changed scope closes without historical intent

When fresh Git observation reports no changed paths, `ethos plan --changed`
SHALL return a successful no-op result without selecting active or archived
OpenSpec intent, compiling proof gates, or applying historical archive scope to
the empty observation.

#### Scenario: Clean repository has no changed-scope work

- **WHEN** `ethos plan --changed --json` runs in a clean governed repository
- **AND** fresh Git observation reports zero changed paths
- **THEN** the result passes with `changed=false` and zero plan nodes
- **AND** the result contains no `proof_archive_scope_stale` gap
- **AND** no active or archived Change is selected as current intent.

#### Scenario: Non-empty changed scope remains governed

- **WHEN** `ethos plan --changed --json` observes one or more changed paths
- **THEN** the current official Change and archive authority rules remain in
  force
- **AND** stale or insufficient archive scope still fails closed.
