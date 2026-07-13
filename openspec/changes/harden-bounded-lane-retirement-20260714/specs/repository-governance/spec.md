## ADDED Requirements

### Requirement: Bounded landed Work Lane retirement tolerates unrelated missing paths

ETHOS SHALL scope `ethos lane retire landed --branch <branch>` inspection to
the requested Work Lane before performing lane-local Git status checks. An
unavailable selected worktree path SHALL fail closed as non-retireable and
SHALL NOT raise an unhandled exception, delete a ref, or mutate any unrelated
Work Lane.

#### Scenario: Foreign historical worktree is unavailable

- **GIVEN** an unrelated foreign Work Lane remains registered with a missing
  filesystem path
- **WHEN** the matching owner retires a different clean, merged Work Lane by
  explicit branch and expected head
- **THEN** ETHOS evaluates and retires only the selected Work Lane
- **AND THEN** the unavailable foreign Work Lane remains untouched.

#### Scenario: Selected worktree is unavailable

- **WHEN** landed retirement selects a Work Lane whose path is unavailable
- **THEN** ETHOS returns a blocked non-retireable result for that lane
- **AND THEN** it does not delete the selected ref or any linked worktree.
