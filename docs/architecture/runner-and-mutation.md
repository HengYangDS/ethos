---
subject: ethos:runner-mutation
role: reference
state: canonical
relations:
  canonical_for: workspace execution boundary
---

# Runner And Mutation Boundary

ETHOS separates planning from execution. The kernel emits an action graph; the
workspace layer chooses a runner.

Initial runners are deliberately small:

- `DryRunRunner` records the action without side effects.
- `LocalSubprocessRunner` executes a node in a chosen repository root.
- Future Dagger, hosted CI, Temporal, or remote agent runners must consume the
  same action graph contract.

Tracked mutation is gated by a mutation decision. `ethos land --apply` and
`ethos publish --apply` require explicit authorization and an expected HEAD.
Without both, the command returns `authorization_required` or
`expect_head_required` instead of mutating.

Tracked file edits must pass Work Lane admission before an agent writes. `ethos
lane start` creates an owned Work Lane branch under the configured prefix,
binds it to a linked worktree, and records a local lease. `ethos lane status`
exposes linked worktrees and foreign Work Lanes from the accepted root without
entering those foreign worktrees. `ethos lane prewrite` rejects tracked writes
from protected roles and requires the editor root to match the owned Work Lane.

The local candidate train is the configured candidate branch bound to its own
linked worktree. `ethos lane candidate --apply` bootstraps that worktree from a
clean accepted root with an expected HEAD. New Work Lanes start from the
candidate branch instead of the accepted root, and `ethos land --apply` from an
admitted Work Lane fast-forwards the candidate worktree without advancing the
accepted root.
Status output reports configured `role_policy` and role-policy
`branch_bindings` in semantic order:
release_root -> accepted_root -> candidate -> work_lane -> submit_lane.
Existing linked worktrees report `worktree_binding = "linked"` as product
state; host-specific open or checkout labels are adapter projections, not
workspace semantics. Adapters derive presentation from `worktree_binding`; they
do not own branch role, lane, or mutation semantics.
`ethos lane start --apply --json` returns the newly created Work Lane under
`data.worktree` with the same binding vocabulary. Start admission also rejects a
dirty candidate worktree with `candidate_worktree_dirty`, so a new Work Lane
cannot be created from ambiguous local candidate state.

Status output also carries `closeout_support`. Only the current clean
Work Lane checkout can advertise `operation = "land_to_candidate"`. Release
roots, accepted roots, candidate branches, submit lanes, detached heads, and
foreign Work Lanes remain observe-only and report blocking gaps such as
`protected_root_mutation`, `work_lane_dirty`, `candidate_worktree_missing`, or
`candidate_worktree_dirty`.

`ethos publish` is a local readiness command until a remote publication adapter
is available. It reports `remote_push = "not_performed"` and a
`publication.mode = "local_readiness"` package with the planned submit branch
under the configured submit prefix. Remote push is deliberately deferred; local
proof and candidate closeout are still the required preparation.

The publication payload also carries `publication.local_submit_package`, a
non-blocking package that records the source branch, planned submit branch,
deferred remote state, and required local steps: land the Work Lane to the
candidate branch, fast-forward the accepted root from the candidate branch, then
create and push the configured submit branch when remote publication is
available. `ethos campaign closeout` aggregates this package with workspace
closeout support, release policy, parity backlog, and shadow parity execution
packages, but it remains read-only; actual mutation still goes through
`ethos land --apply`.

This keeps break-glass paths explicit and makes dry-run planning safe by
default.
