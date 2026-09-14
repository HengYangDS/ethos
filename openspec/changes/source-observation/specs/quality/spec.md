## ADDED Requirements

### Requirement: Source Identity Observation Is Bounded And Coordinate-Consistent

Source-build identity SHALL bind one observed commit and the complete effective
non-ignored overlay without changing the caller's index or working files. The
observation SHALL finish within one declared time budget or retain a typed
failure. HEAD movement during observation SHALL prevent a successful identity.

#### Scenario: HEAD moves while the overlay is observed

- **WHEN** HEAD changes after the initial source coordinate is read
- **THEN** identity observation rejects the mixed observation rather than returning
  the first commit paired with an independently selected later baseline.

#### Scenario: A native source query reaches its deadline

- **WHEN** a Git step exhausts the source observation's total deadline
- **THEN** the result retains command, root, timeout and available process evidence,
  removes its owned temporary index, and does not report a valid identity.

#### Scenario: Local overlay and index-only flags differ

- **WHEN** staged, unstaged, untracked, deleted or mode-changed content is present
- **THEN** the observer retains native full-overlay meaning, does not use a
  metadata-only shortcut, and preserves the caller's index bytes.

### Requirement: Closeout Projections Observe Only Their Required Facts

A closeout command or bootstrap projection SHALL consume the existing exact ref
and worktree topology owners without re-running unrelated runtime or Lease
admission. This reduction SHALL NOT replace the fresh checks performed before an
actual effect or reuse prior authorization.

#### Scenario: A command needs only the accepted worktree and candidate object

- **WHEN** the closeout projection derives its exact target command
- **THEN** the command uses the configured roles and current required coordinates
  without invoking the complete workspace-status collector.

#### Scenario: Candidate changes before an accepted effect

- **WHEN** candidate advances after the earlier closeout observation
- **THEN** fresh effect admission rejects stale coordinates despite any already
  rendered command or bootstrap projection.
