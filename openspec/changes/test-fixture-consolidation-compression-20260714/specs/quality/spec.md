## ADDED Requirements

### Requirement: Declarative Work-Lane Admission Test Partitions

ETHOS SHALL represent finite equivalent Work-Lane admission failure states as
bounded declarative test partitions when the formatter-clean scoped test
representation is a net deletion and each state-specific setup, blocking gap,
and no-worktree invariant remains explicit.

#### Scenario: Candidate readiness states remain independently covered

- **WHEN** the candidate branch is missing, the candidate worktree is missing,
  or the candidate worktree is dirty
- **THEN** a distinct declarative test case SHALL assert the corresponding
  blocking gap
- **AND THEN** no requested Work Lane checkout SHALL be created.

#### Scenario: Accepted-root start blockers remain independently covered

- **WHEN** a nested Work Lane start is requested from a Work Lane or the
  accepted root is dirty
- **THEN** a distinct declarative test case SHALL assert
  `lane_start_requires_clean_accepted_root`
- **AND THEN** no requested Work Lane checkout SHALL be created.
