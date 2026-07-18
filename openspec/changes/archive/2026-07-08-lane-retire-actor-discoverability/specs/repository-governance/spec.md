# repository-governance Delta

## MODIFIED Requirements

### Requirement: Landed Work Lane Retirement

ETHOS SHALL govern local landed Work Lane cleanup through explicit,
head-bound command semantics rather than raw Git worktree or branch deletion.

#### Scenario: landed Work Lane retirement actor authority is visible

- **GIVEN** a linked Work Lane has an active lease owner
- **WHEN** `ethos lane retire-landed --branch <branch> --expect-head <head>
  --apply --json` runs without an actor binding matching the lease owner
- **THEN** ETHOS refuses cleanup with `foreign_work_lane_retire_authority_required`
- **AND** the command payload exposes the actor source, current actor binding
  state, required lease owner, selected ref, and expected head
- **AND** the command emits a bounded next action to bind the actor or obtain
  owner handoff
- **AND** the Work Lane worktree and branch ref remain present
