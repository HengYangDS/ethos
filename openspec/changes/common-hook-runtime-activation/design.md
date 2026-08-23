## Context

The runtime package and generated hook launchers already live under
`<git-common-dir>/ethos/**`, but activation is written with worktree-scoped Git
configuration. A linked worktree can therefore keep an older `core.hooksPath`
after another worktree installs a new source-bound runtime. The result is one
physical runtime owner with multiple effective activation owners.

## Goals / Non-Goals

**Goals:**

- Make effective activation a repository-common fact inherited by every linked
  worktree.
- Remove worktree-local activation overrides instead of updating them in a loop.
- Observe all linked worktrees before reporting success.
- Delete obsolete generated paths only from an exact consumer inventory.

**Non-Goals:**

- Treat Git hooks as an adversarial security boundary.
- Add a runtime registry, migration ledger, compatibility launcher, or fallback.
- Change product-specific hook policy or adopter quality commands.

## Decisions

### Common Git config owns activation

Write `core.hooksPath` and the required ref-storage policy in repository-common
Git config. Remove the corresponding worktree-scoped keys from every linked
worktree so inheritance has one source. This is preferable to synchronizing N
copies because synchronization preserves N authorities and recreates drift.

### Existing Git-common directories remain the only generated owners

Keep immutable runtimes under `<git-common-dir>/ethos/runtime/<digest>` and
launchers under `<git-common-dir>/ethos/hooks/<digest>`. The change alters
activation and garbage collection only; it does not introduce another carrier.

### Cleanup is consumer-derived and post-observed

Build the keep set from effective common/worktree Git config, launcher runtime
locators, and current operation references. Delete only generated directories
outside that set, then re-observe all linked worktrees and the filesystem. A
missing or unreadable consumer source fails closed.

## Risks / Trade-offs

- **Concurrent Git config mutation** → bind writes and cleanup to the observed
  common directory and verify all effective values afterward.
- **Deleting a still-used immutable runtime** → derive a complete keep set and
  block on unknown consumers rather than guessing from age.
- **Existing worktree overrides mask common config** → remove the exact owned
  keys from every linked worktree before declaring convergence.

## Migration Plan

1. Materialize the current immutable runtime and launcher generation.
2. Write the repository-common activation.
3. Remove owned worktree-local overrides from all linked worktrees.
4. Verify every linked worktree resolves the common activation.
5. Retire only unreferenced generated generations and post-observe the result.

Rollback restores the previously observed common activation and exact
worktree-local values before removing any newly created unconsumed generation.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:Git-common hook runtime activation is singular` | `1.1` | `tests/unit/cli/test_hook_runtime.py` multi-worktree activation regression |
| `repository-governance:Git-common hook runtime activation is singular` | `1.2` | fail-closed consumer and unreadable-config regressions |
| `command-plane:Hook installation reports repository-wide convergence` | `3.2` | hook-install JSON projection regression |
