# Accepted-to-release fast-forward mirror

## Why

ETHOS accepted closeout could advance `dev` while the release branch remained an
independent local ref. Repositories that deliberately make release a
fast-forward mirror need that relationship to be declarative, proof-bound, and
unbypassable rather than a raw Git convention.

## What Changes

- Add the opt-in `branch_roles.release_mirror = "accepted_ff"` mode.
- Read mirror policy from the candidate commit tree for protected release-ref
  admission.
- Advance accepted and release refs in one compare-and-swap transaction, with
  one exact closeout intent per ref and the same executed proof binding.
- Synchronize a linked release worktree after the transaction and fail closed
  if reset or post-sync cleanliness verification fails.
- Keep the default `independent` release mode unchanged.

## Boundary

This change does not permit raw protected-ref moves, bypass proof requirements,
or mutate foreign Work Lanes. The only enabled release move is the official
accepted closeout to the exact proven candidate head.
