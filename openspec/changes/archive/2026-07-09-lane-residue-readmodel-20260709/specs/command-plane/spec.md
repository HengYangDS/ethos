# lane-coordination Spec Delta

## ADDED Requirements

### Requirement: Landed dirty lanes expose preservation guidance

Foreign Work Lane records with `closeout_disposition = landed_dirty` SHALL expose a residue state and a next action that instructs the owner to preserve or intentionally discard the dirty worktree delta before retirement.

#### Scenario: linked landed lane has unpreserved worktree delta

- **GIVEN** a linked Work Lane branch is an ancestor of the accepted root
- **AND** its linked worktree has dirty tracked or untracked paths
- **WHEN** `ethos status --json` reports the foreign Work Lane
- **THEN** the lane reports `closeout_disposition = landed_dirty`
- **AND** the lane reports `residue_state = unpreserved_worktree_delta`
- **AND** the lane reports a next action requiring owner preservation or intentional discard before retirement
- **AND** the lane remains observe-only for non-owning actors
