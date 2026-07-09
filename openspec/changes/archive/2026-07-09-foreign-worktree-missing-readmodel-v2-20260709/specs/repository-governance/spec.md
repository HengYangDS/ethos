## MODIFIED Requirements

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance, SHALL expose unbound Work Lane
refs as inspectable residue objects rather than count-only signals, and SHALL
surface missing foreign Work Lane and candidate physical paths without crashing reader views.

#### Scenario: Foreign Work Lane missing physical path is fail-soft and observe-only

- **GIVEN** Git worktree metadata advertises a foreign `work/*` Work Lane path
- **AND** that physical path no longer exists
- **WHEN** `ethos status --json` or accepted-root closeout readiness reads Work
  Lane coordination state
- **THEN** ETHOS reports the foreign lane with `worktree_binding=missing`
- **AND** the reader does not crash while inspecting dirty paths
- **AND** `dirty=false` and `dirty_paths=[]` because no dirty filesystem state is
  observable at that path
- **AND** coordination remains advisory for accepted-root readers
- **AND** the payload grants no write, land, retire, or cleanup authority over
  the foreign lane

#### Scenario: Candidate Worktree missing physical path is fail-soft

- **GIVEN** Git worktree metadata advertises the configured candidate worktree path
- **AND** that physical path no longer exists
- **WHEN** `ethos status --json` reads workspace status
- **THEN** ETHOS reports the candidate with `worktree_binding=missing`
- **AND** `worktree_exists=false`
- **AND** readiness reports `candidate_worktree_missing` instead of crashing while
  checking candidate dirty state
- **AND** if the candidate path disappears during dirty inspection, ETHOS treats
  the candidate state as unsafe to close out rather than crashing
