## Why

Hook launchers and immutable runtimes live under one Git common directory, but
activation is currently written into each worktree's local Git config. Linked
worktrees can therefore retain different hook generations, become stale after
accepted HEAD moves, and require repetitive repair despite sharing one runtime
owner.

## What Changes

- Make the Git common directory the single owner of effective hook/runtime
  activation for all linked worktrees.
- Remove stale worktree-local `core.hooksPath` and `gc.packRefs` overrides when
  installing or repairing the common activation.
- Observe every linked worktree after activation and fail closed if any still
  resolves a different hook generation.
- Retire obsolete generated hook/runtime generations only after proving that no
  linked worktree or active launcher consumes them.
- Keep Git hooks accurately described as same-user-bypassable fallback guards;
  this change does not elevate them into repository authority.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: one Git common directory has one effective local
  hook/runtime activation inherited by every linked worktree, with exact stale
  projection detection and retirement.
- `command-plane`: `ethos hook install` reports the common activation and the
  linked-worktree convergence/cleanup result as one precise operation.

## Impact

This changes the existing hook installer, Git-config effect owner, runtime
binding observation, linked-worktree repair, focused tests, and their public
documentation. It adds no second runtime registry, compatibility reader, or
adopter-specific exception.
