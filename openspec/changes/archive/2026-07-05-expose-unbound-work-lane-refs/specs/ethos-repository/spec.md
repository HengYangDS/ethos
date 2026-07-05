## ADDED Requirements

### Requirement: Unbound Work Lane Ref Visibility

ETHOS SHALL expose configured Work Lane branch refs in workspace status even
when no linked Git worktree exists for the branch.

#### Scenario: Unbound Work Lane ref is visible but not active

- **GIVEN** a configured Work Lane branch ref exists
- **AND** no linked Git worktree exists for that branch
- **WHEN** `ethos status --json` runs
- **THEN** `branch_bindings` includes the branch with `role=work_lane` and
  `worktree_binding=unbound`
- **AND** `foreign_work_lanes` does not include that branch
- **AND** coordination reports an advisory unbound Work Lane ref signal without
  treating the ref as a blocking closeout gap.
