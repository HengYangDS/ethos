# repository-governance Delta

## ADDED Requirements

### Requirement: Publish readiness distinguishes observed remote synchronization from execution

`ethos publish` SHALL keep local readiness, remote observation, remote mutation,
and hosted CI as separate evidence classes.

#### Scenario: Synchronized tracking ref is reported without a new push

- **WHEN** `ethos publish --probe-remote --json` observes the local tracking ref
  for the current branch at the same HEAD as the checkout
- **THEN** `summary.remote_publication_state` and
  `data.publication.remote_state` SHALL be `synchronized`
- **AND** `remote_push` SHALL remain `not_performed`
- **AND** the mutation verdict SHALL remain `defer`
- **AND** the next action SHALL state that no push was performed

#### Scenario: Reachable but non-synchronized remote remains deferred

- **WHEN** the remote is available but the tracking comparison is not
  `synchronized`
- **THEN** `data.publication.remote_state` SHALL remain `deferred`
- **AND** the command SHALL not claim a remote push or hosted-CI result
