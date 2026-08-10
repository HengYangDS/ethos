## Why

A failed linked-lane retirement can remove its clean worktree before the exact
ref transaction is rejected. If compensation cannot recreate that worktree,
the repository retains the exact Work Lane ref and valid Lease but exposes no
public path back to the linked retirement owner. The lane is then neither a
linked target nor an unleased absorbed ref, so safe lifecycle convergence is
impossible without forbidden manual Git or SQLite mutation.

## What Changes

- Extend superseded linked retirement with one explicit no-clobber recovery
  path for an absent worktree whose ref, Lease generation, holder, HEAD, tree,
  Commitment, and absorption authority still match exactly.
- Recreate that one linked worktree through the existing worktree-effect owner,
  then continue through the existing linked retirement transaction.
- Preserve the recovered worktree whenever the subsequent retirement effect
  blocks, and retain the exact recovery failure in structured command output.
- Add real installed-hook and partial-state lifecycle regressions.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=linked-retirement-partial-recovery;
  reuse=extend; change=modify; facet:lifecycle=retirement;
  facet:authority=lease,git-ref,worktree,public-command.

## Out of Scope

Raw ref deletion, Lease edits, path replacement, foreign-holder takeover,
unleased absorbed-ref retirement, generic worktree repair, and adopter mutation.
