# repository-governance Delta

## MODIFIED Requirements

### Requirement: Accepted-root closeout success has a clean-checkout postcondition

`accepted_validated` MUST be emitted only when the accepted checkout is clean
after the accepted-ref CAS and worktree/index synchronization.

#### Scenario: Clean postcondition admits closeout

- **WHEN** closeout sync succeeds and `git status --short` is empty
- **THEN** ETHOS may report `accepted_validated`

#### Scenario: Dirty postcondition blocks closeout success

- **WHEN** closeout sync succeeds but `git status --short` is non-empty
- **THEN** ETHOS reports `accepted_worktree_dirty_after_sync`
- **AND** ETHOS does not report `accepted_validated`

### Requirement: Mutation admission rejects promoted active OpenSpec carriers

OpenSpec active changes are legal authoring carriers in Work Lanes only while
they are in progress. A completed active change MUST be archived before landing,
and candidate or accepted-root promotion MUST reject any active carrier left under
`openspec/changes/<id>`.

#### Scenario: Completed active carrier blocks landing

- **WHEN** a Work Lane contains an OpenSpec change whose task checkboxes are all complete
- **THEN** mutation admission reports `openspec_completed_change_unarchived:<id>`
- **AND** the Work Lane does not advance to candidate

#### Scenario: Active carrier blocks closeout roots

- **WHEN** accepted-root closeout sees an active carrier in accepted or candidate truth
- **THEN** mutation admission reports `openspec_active_change_unarchived:<id>:<role>`
- **AND** accepted-root closeout does not report `accepted_validated`
