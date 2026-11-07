# Proposal

## Why

`ethos lane housekeeping --apply --authorize` removes clean detached worktrees below temporary roots.
It never checks that a ref still reaches the worktree's `HEAD`, and `git status --porcelain` does
not report ignored files, which `git worktree remove` deletes. A detached worktree can therefore hold
the only copy of a commit or of ignored content, and housekeeping removes it (register row 28). The
product design contract retires a clean worktree only after checking its ref, worktree, owner and
unique content.

## What Changes

- Housekeeping skips and reports a detached worktree when no retaining ref reaches its `HEAD`:
  `worktree_head_unreachable`, or `worktree_reachability_unavailable` when Git cannot answer.
  Retaining refs are heads, tags, remote-tracking refs and `refs/keep/*`.
- It also skips and reports a worktree that holds ignored files outside the regenerable roots, with
  `worktree_ignored_content`. Those roots are a root `.venv`, a root `node_modules`, and a
  `__pycache__` whose bytecode all sits beside its source.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: detached worktree housekeeping protects unique commits and ignored
  content.

## Impact

- `src/ethos/adapters/mutation/worktree/detached_cleanup.py` and
  `tests/unit/lanes/test_worktree_housekeeping.py`.
