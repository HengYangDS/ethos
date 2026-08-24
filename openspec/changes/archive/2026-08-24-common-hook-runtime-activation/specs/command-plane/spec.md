## ADDED Requirements

### Requirement: Hook installation reports repository-family convergence

`ethos hook install` SHALL project one Git-common activation operation rather
than only the invoking worktree.

#### Scenario: Installation converges linked worktrees

- **WHEN** hook installation succeeds from any linked worktree
- **THEN** JSON reports the effective common hooks path and immutable runtime identity
- **AND** it lists every linked worktree as checked or repaired
- **AND** it lists exact checked, removed, and retained generated paths
- **AND** `next_action` is empty because no further repair is required.

#### Scenario: Installation cannot establish convergence

- **WHEN** a linked worktree or generation consumer cannot be observed exactly
- **THEN** installation returns a non-pass verdict before deleting a generated path
- **AND** `next_action` is the complete root-bound `ethos hook install` command.
