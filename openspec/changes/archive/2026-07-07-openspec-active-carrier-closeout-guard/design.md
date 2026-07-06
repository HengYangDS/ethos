## Context

OpenSpec changes are carriers, not current truth. A Work Lane may keep an active
carrier while authoring, but candidate and accepted-root states must not retain
active carriers after promotion.

## Design

Repository OpenSpec shape audit now derives the current branch role from the
configured branch-role policy. If the role is `candidate` or `accepted_root`, any
active change directory under `openspec/changes/` except `archive` emits
`openspec_active_change_unarchived:<change>:<role>`. This gap flows through
repository audit, report, prove, land, and closeout.

The existing completed-change guard remains as a narrower signal for Work Lanes:
if all tasks are checked but the change is still active, it should be archived
before land.

## Proof Strategy

- Unit tests cover active-change gaps for work-lane, candidate, and accepted-root
  roles.
- Repository audit/report/proof exercise the same OpenSpec shape report.
- OpenSpec archive closeout validates both archived carriers.
