# repository-governance Delta

## ADDED Requirements

### Requirement: Superseded Linked Work Lane Retirement

ETHOS SHALL govern cleanup of clean linked Work Lanes whose semantic truth has
already been absorbed into accepted root without requiring their stale branch
content to be landed.

#### Scenario: superseded linked Work Lane retirement is head, actor, reason, and absorption bound

- **GIVEN** a linked clean `work/*` Work Lane is not merged into accepted root
- **WHEN** `ethos lane retire-superseded --branch <branch> --expect-head <head>
  --absorbed-by <accepted-head> --reason <why> --authorize --apply --json` runs
- **THEN** ETHOS removes the linked worktree and deletes `refs/heads/<branch>`
  only if `<head>` still matches the branch, `<accepted-head>` equals the current
  accepted root, the lane lease owner matches `ETHOS_ACTOR`, and a reason is
  supplied
- **AND** the command emits the retired lane, reason, absorption head, mutation
  binding, and required gaps

#### Scenario: superseded linked Work Lane retirement fails closed

- **WHEN** the lane is missing, unlinked, dirty, already merged, actor mismatched,
  head mismatched, absorption head stale or missing, reason missing, or apply
  lacks authorization
- **THEN** ETHOS refuses cleanup and reports deterministic required gaps
- **AND** the Work Lane worktree and branch ref remain present
