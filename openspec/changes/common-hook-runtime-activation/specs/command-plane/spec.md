## ADDED Requirements

### Requirement: Hook installation reports repository-wide convergence
`ethos hook install` SHALL expose the single Git-common activation, linked
worktree convergence, and exact cleanup result rather than reporting only the
invoking worktree.

#### Scenario: Installation result is actionable and complete
- **WHEN** hook installation or repair finishes
- **THEN** its JSON reports the effective common hooks path and immutable runtime
  identity
- **AND** it reports every linked worktree that was checked or repaired
- **AND** it reports exact removed and retained generated paths
- **AND** any unresolved worktree or cleanup ambiguity produces one executable
  next action and a non-pass verdict.
