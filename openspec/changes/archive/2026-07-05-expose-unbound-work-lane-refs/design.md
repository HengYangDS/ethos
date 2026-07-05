## Context

OpenSpec carries this repository governance semantics change. The ETHOS product
boundary remains Git-native repository status: Git refs and worktrees are source
facts, leases remain local state, and status JSON is the inspectable read model.

## Design

`branch_bindings` becomes the single status read model for configured branch refs
and linked worktree branches. It already reports configured release, accepted,
and candidate refs, plus linked worktrees. The change extends that model to also
include configured `work/*` refs that have no linked worktree. These entries use
`role=work_lane`, `worktree_binding=unbound`, empty `worktree_path`, and claim
state derived from any available lease.

`foreign_work_lanes` remains limited to linked worktrees. That boundary matters:
a linked worktree can expose dirty paths, path scope, and lease state; an
unbound ref only exposes branch and HEAD. ETHOS should surface it as an advisory
coordination signal, not as an active lane or blocking conflict.

`coordination` adds `unbound_work_lane_count`, and `coordination_gaps` includes
`unbound_work_lane_ref_present` when any such ref exists. The detailed branches
are available in `branch_bindings`, preserving SSOT and avoiding a duplicate
list.

## Alternatives

Adding unbound refs to `foreign_work_lanes` was rejected because it would blur
active worktree state with inert Git refs and would force fake dirty-path or
scope fields. Adding a new top-level list was rejected because `branch_bindings`
already owns branch/ref binding visibility.

## Proof Strategy

- Validate the OpenSpec change with `openspec status --change expose-unbound-work-lane-refs --json`.
- Add unit and CLI contract tests covering an unbound `work/*` ref.
- Validate `workspace-status.schema.json` with status payload fixtures.
- Run focused lane/status tests, schema tests, and head-bound `ethos prove`.
