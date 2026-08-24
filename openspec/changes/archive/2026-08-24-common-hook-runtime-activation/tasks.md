## 1. Contract and reproducer

- [x] 1.1 Add a multi-worktree regression proving one hook install removes stale worktree-local activation overrides and makes every linked worktree resolve one common generation; verify the test fails against the incumbent installer.
- [x] 1.2 Add fail-closed regressions for unreadable linked-worktree config and an observed generation consumer; verify no generated path is deleted in either case.

## 2. Single activation owner

- [x] 2.1 Move hook activation from worktree-local Git config to the repository-common config owner and delete the incumbent per-worktree activation writes; verify the multi-worktree regression passes.
- [x] 2.2 Remove owned stale `core.hooksPath` and `gc.packRefs` worktree overrides across all linked worktrees and verify post-observation reports one effective value.
- [x] 2.3 Update linked-worktree recovery to consume the common activation instead of writing another local projection; verify retirement recovery tests pass.

## 3. Consumer-aware cleanup and result

- [x] 3.1 Derive the exact keep set for generated hook/runtime generations from current config, launchers, and active operation references; verify unknown consumers block deletion.
- [x] 3.2 Retire only unreferenced generated generations, post-observe the filesystem, and expose exact checked/repaired/removed/retained paths in the existing hook-install result.
- [x] 3.3 Remove obsolete helper branches and tests that encode per-worktree activation as valid; verify repository-wide reference closure.

## 4. Closeout

- [x] 4.1 Run format before lint, focused hook/runtime and retirement tests, OpenSpec strict validation, and changed proof readiness.
- [x] 4.2 Run the full applicable proof once on the frozen HEAD.
