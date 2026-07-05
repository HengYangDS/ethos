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
The write boundary is deliberately ordered: target path, repository root,
context refresh, status, prewrite, write, then post-write audit. This order keeps
mutation bound to repository truth instead of a shell cwd, editor tab, or agent
host assumption.

The local candidate train is the configured candidate branch bound to its own
linked worktree. `ethos lane candidate --apply` bootstraps that worktree from a
clean accepted root with an expected HEAD. New Work Lanes start from the
candidate branch instead of the accepted root, and `ethos land --apply` from an
admitted Work Lane fast-forwards the candidate worktree without advancing the
accepted root. `ethos land --json` checks the same ancestry before mutation; if
the candidate train has advanced since the Work Lane started, it reports
`candidate_base_stale` and points to `ethos lane refresh-base` instead of
waiting for apply mode to discover the stale base. If the candidate train and
accepted root diverge before accepted-root closeout, closeout reports
`candidate_diverged_from_accepted` and points to
`ethos lane candidate --refresh-from-accepted --apply --authorize --expect-head <head> --json`
so the train can be reset deliberately before the Work Lane is replayed.
Status output reports configured `role_policy` and role-policy
`branch_bindings` in semantic order:
release_root -> accepted_root -> candidate -> work_lane -> submit_lane.
Existing linked worktrees report `worktree_binding = "linked"` as product
state; host-specific navigation labels are adapter projections, not workspace
semantics. Adapters derive presentation from `worktree_binding`; they do not
own branch role, lane, or mutation semantics.
Foreign Work Lanes appear in `foreign_work_lanes` and in the `coordination`
package. Presence is advisory when scopes are disjoint or the current checkout
is observe-only. Candidate integration from a Work Lane is blocking when the
current lane and a foreign lane have overlapping or unknown path scope; the
status payload reports `coordination_gap:*` in `required_gaps` before a later
merge can accidentally let one agent overwrite another agent's obligation.
`ethos lane start --apply --json` returns the newly created Work Lane under
`data.worktree` with the same binding vocabulary. Start admission also rejects a
dirty candidate worktree with `candidate_worktree_dirty`, so a new Work Lane
cannot be created from ambiguous local candidate state.
The standard Work Lane lifecycle is command-bound: `ethos lane start` creates
and leases the lane, `ethos lane bind-claim` attaches claim boundary evidence
when needed, `ethos lane refresh-base` replays a stale lane onto the configured
candidate branch, `ethos land` advances the configured candidate branch, and
`ethos lane retire-landed` removes only an explicitly named landed Work Lane.
Raw Git worktree creation can exist as a repository fact, but it is not standard
ETHOS workflow state.

Status output also carries `closeout_support`. Only the current clean
Work Lane checkout can advertise `operation = "land_to_candidate"`. Release
roots, accepted roots, candidate branches, submit lanes, detached heads, and
foreign Work Lanes remain observe-only and report blocking gaps such as
`protected_root_mutation`, `work_lane_dirty`, `candidate_worktree_missing`, or
`candidate_worktree_dirty`.

Accepted-root closeout is the matching protected-root mutation. It runs through
the ETHOS command plane from a current ETHOS runner:

```bash
ethos land --closeout --apply --authorize --expect-head <accepted-head> --root <accepted-root> --json
```

The command audits the configured candidate worktree first, and only then
fast-forwards the accepted branch from the candidate branch. The
`closeout_bootstrap` package in `ethos land --closeout --json` records the
accepted root, audit root, configured branches, heads, blocking gaps, and exact
command so the handoff is product state rather than a host UI, assistant
runtime, or shell convention. Its mode is `maintainer_break_glass_local`: a
current ETHOS runner is allowed to execute the protected closeout with an
explicit `--root <accepted-root>`, while remote push remains `deferred` and the
candidate worktree is audited before accepted-root movement.

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

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
