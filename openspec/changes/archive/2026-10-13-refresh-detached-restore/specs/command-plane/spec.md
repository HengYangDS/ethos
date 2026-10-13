## ADDED Requirements

### Requirement: Refused and interrupted refreshes restore their Work Lane

`ethos lane refresh-base` SHALL return a lane whose rewritten head was refused to its original head with its branch attached, and SHALL restore a lane left detached by an interrupted refresh from that lane's pending refresh record.

#### Scenario: A refresh effect is refused after the rebase

- **WHEN** replay validation or the lane ref update of a refresh is refused
- **THEN** the lane's HEAD, index and worktree return to the original head
- **AND** the lane branch is attached again.

#### Scenario: A refresh was interrupted after the rebase

- **WHEN** a lane is detached with no applied refresh effect and its pending record names a branch that still holds the recorded head
- **THEN** `refresh-base --apply` restores the lane to that head with its branch attached and reports `base_restored`
- **AND** its next action is the exact refresh of the restored head.

#### Scenario: The pending record does not match

- **WHEN** the lane is dirty, a rebase is unfinished or the branch no longer holds the recorded head
- **THEN** the refresh blocks without moving the worktree.
