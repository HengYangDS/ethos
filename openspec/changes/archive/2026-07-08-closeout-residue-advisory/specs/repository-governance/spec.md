## MODIFIED Requirements

### Requirement: Context-bound mutation admission

ETHOS SHALL bind tracked mutation admission to explicit repository root,
checkout role, editor root, and target paths before a write-capable tool can
mutate tracked files. ETHOS SHALL also reject hidden change carriers that bypass
repository truth surfaces.

#### Scenario: Sanctioned Work Lane replay keeps admission context

- **GIVEN** `ethos lane refresh-base --apply --authorize --expect-head <head>`
  is replaying a clean owned Work Lane onto the configured candidate branch
- **WHEN** Git temporarily detaches HEAD during rebase and the commit-time
  fallback hook evaluates staged tracked paths
- **THEN** mutation admission derives the effective branch role from Git rebase
  `head-name` only when it names a configured `work/*` branch
- **AND** the hook still checks the same repository root, editor root, runtime
  binding, and target paths
- **AND** detached replay for accepted, candidate, submit, other, or unknown
  branches remains protected and fails closed

### Requirement: Work Lane Coordination Read Model

ETHOS SHALL distinguish blocking Work Lane coordination gaps from advisory
coordination signals in status command guidance, and SHALL expose unbound Work
Lane refs as inspectable residue objects rather than count-only signals.

#### Scenario: Foreign Work Lanes expose closeout disposition without authority

- **GIVEN** a repository has a linked foreign `work/*` worktree
- **WHEN** `ethos status --json` reports that lane in `data.foreign_work_lanes`
- **THEN** the lane item exposes `relation_to_accepted` and
  `closeout_disposition` derived from Git relation, dirty state, lease, and
  claim binding
- **AND** closeout residue appears as a coarse advisory coordination signal
  rather than one branch-level gap per disposition
- **AND** missing leases remain distinct from retire-ready closeout disposition
- **AND** `ethos report --json` routes that advisory signal to read-only
  inspection commands
- **AND** the disposition does not grant write, land, retire, or cleanup
  authority over that Work Lane
