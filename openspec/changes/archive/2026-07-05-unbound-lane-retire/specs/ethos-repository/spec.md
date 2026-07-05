## ADDED Requirements

### Requirement: Unbound Work Lane Ref Retirement

ETHOS SHALL govern local unbound Work Lane ref cleanup through explicit,
head-bound command semantics rather than raw Git branch deletion.

#### Scenario: unbound Work Lane ref retirement is head-bound

- **GIVEN** `ethos status --json` exposes an unbound Work Lane ref in
  `data.coordination.unbound_work_lane_refs`
- **WHEN** `ethos lane retire-unbound --branch <branch> --expect-head <head>
  --reason <why> --authorize --apply --json` runs
- **THEN** ETHOS deletes `refs/heads/<branch>` only if the branch is still an
  unbound configured Work Lane ref and its current head equals `<head>`
- **AND** the command emits the retired ref, reason, expected head, authorization
  state, relation to accepted truth, and required gaps

#### Scenario: unbound Work Lane ref retirement fails closed

- **WHEN** the target branch is missing, not a Work Lane, linked to a worktree,
  has a mismatched expected head, lacks a reason, or apply lacks authorization
- **THEN** ETHOS refuses deletion and reports deterministic required gaps
- **AND** the branch ref remains present
