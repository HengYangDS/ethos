## MODIFIED Requirements

### Requirement: Work Lane Topology

ETHOS SHALL classify linked worktrees by local repository role and SHALL keep remote review refs
outside local authoring authority. ETHOS SHALL report each worktree from one whole Git record, so
its path, head, branch or detached state, lock and prune state, and their reasons are exactly the
values Git records, even when one of them holds a newline.

#### Scenario: Role policy is projected

- **WHEN** `ethos status --json` or `ethos lane status --json` reports workspace topology
- **THEN** local role order is `release_root -> accepted_root -> candidate -> work_lane`
- **AND** a configured `proposal/*` target is classified only by publication admission as
  `proposal_ref`
- **AND** no proposal ref grants local authoring or Lease authority.

#### Scenario: Foreign Work Lanes exist

- **WHEN** `ethos status` or `ethos lane status` inspects a repository with a
  linked `work/*` lane outside the current checkout
- **THEN** ETHOS reports the foreign lane path, branch, head, and role from Git
  worktree metadata
- **AND** ETHOS reports `foreign_work_lane_present` as a coordination signal
- **AND** ETHOS does not read, modify, close, or clean the foreign lane
- **AND** ETHOS reports a non-authoritative action preview with observe as the
  only candidate action and write, land, and retire blocked
- **AND** actual mutation re-evaluates its exact current request.

#### Scenario: Worktree records are reported whole

- **WHEN** `ethos lane status --json` reports workspace topology while a worktree's path or lock
  reason holds a newline, or a worktree is locked or prunable
- **THEN** each `data.worktrees` entry comes from one Git record and reports its exact `path`, its
  `head` and its `branch`, which is `detached` when Git records no branch
- **AND** `locked` and `prunable` are `true` or `false`, and `lock_reason` and `prune_reason` hold
  the reason as Git records it, unquoted, or the empty string
- **AND** no worktree is split into another record or merged with one.
