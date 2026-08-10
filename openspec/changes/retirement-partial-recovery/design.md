## Context

Linked retirement currently discovers only registered worktrees. Its
compensation can attempt to recreate a removed worktree, but a failed attempt is
collapsed to a Boolean. The exact residual state therefore becomes invisible to
the command that owns the transition: the branch ref and Lease remain current,
while the registered worktree and path are absent.

## Decision

Keep `lane retire superseded` as the sole semantic owner. Add an explicit
`--path` coordinate used only when the requested `work/*` ref is not linked.
Dry-run compiles a synthetic recovery target only when:

- the ref equals `--expect-head`;
- the current Lease is valid, bound to that HEAD and tree, and held by the
  invoking actor;
- the declared path is absolute, absent, and not registered to another
  worktree;
- the bound Commitment is readable from the expected commit; and
- existing accepted or successor absorption checks still pass.

Apply recreates the exact branch-bound worktree through `add_worktree`, then
re-enters the existing linked-retirement effect. A later block leaves that
recovered worktree linked, restoring the normal retry surface. No second
retirement implementation or raw cleanup path is introduced.

## Alternatives Rejected

- **Allow absorbed-ref with a valid Lease.** This would erase the distinction
  between an owned live generation and an unleased exceptional ref.
- **Delete the ref directly from the residual state.** This bypasses linked
  cleanliness, Commitment, holder, and Lease generation checks.
- **Create a generic worktree-repair command.** The required authority exists
  only as part of this exact retirement transition; a general repair surface
  would mint broader lifecycle authority.

## Risk Controls

- Path collision, symlink, reuse, moved ref, stale tree, invalid Commitment,
  expired or foreign Lease, and actor mismatch block before filesystem effect.
- Recovery is no-clobber and branch-bound.
- Retirement success remains terminal only when Lease, ref, and worktree are
  all absent.
