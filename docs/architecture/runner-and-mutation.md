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
lane start` creates an owned `work/*` linked worktree and records a local lease.
`ethos lane status` exposes linked worktrees and foreign Work Lanes from the
accepted root without entering those foreign worktrees. `ethos lane prewrite`
rejects tracked writes from protected roots and requires the editor root to
match the owned Work Lane.

The local candidate train is `candidate/dev` bound to its own linked worktree.
`ethos lane candidate --apply` bootstraps that worktree from a clean accepted
root with an expected HEAD. New Work Lanes start from `candidate/dev` instead of
raw `dev`, and `ethos land --apply` from an admitted Work Lane fast-forwards the
candidate worktree without advancing `dev`.
Status output marks `candidate/dev` and `work/*` branches that already have
linked worktrees with `action = "open_worktree"` and label `Open Worktree`, not
as plain checkout actions.

This keeps break-glass paths explicit and makes dry-run planning safe by
default.
