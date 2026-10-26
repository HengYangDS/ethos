# Proposal

## Why

When a native Git operation on a protected branch is refused, the reference-transaction hook restores the checkout's exact projection with `restore_rejected_checkout_projection`. It treats any index and worktree that equal the refused target's tree as Git's own projection. A refused new commit meets that condition with the caller's own content. After `git add` and `git commit` on `dev` in the accepted checkout, the hook refuses the commit and then resets the index and worktree to `dev`. The edits survive only in an unreferenced commit that the refusal does not name.

A scratch reproduction with ETHOS's own compensation shows this: the restore reports success, the edited file is back at the accepted content, and the status is empty. The same commit without compensation keeps the edit staged.

Every governed repository runs this hook, and adopters stay on 0.2 until 0.3.0-alpha.1, so the fix ships as 0.2.0-alpha.16.

## What Changes

- Compensation applies only to a target that another ref already contains. That holds for a refused fast-forward, merge, reset or checkout of an existing commit: Git projected that commit, and its content stays reachable after the restore.
- A refused target that no other ref contains holds the caller's own content. Examples are a direct commit, an amend or a cherry-pick on a protected branch. The hook leaves the index and worktree unchanged and names the refused commit in its refusal.
- A changelog entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-transaction`: the requirement "Rejected raw Git transitions fail cleanly or explicitly" restores only a projection of a commit that another ref contains, and never discards content that only the refused operation committed.

## Impact

- Code: `src/ethos/adapters/repo/worktree_effects.py`, `src/ethos/adapters/repo/hook/admission.py` and their tests.
- Refused operations on existing commits are compensated as before.
- A refused reset to a commit that only the reflog holds is no longer compensated: the checkout keeps that content, and the refusal names it.
- Out of scope: the rest of the design v2 review. The 0.3 admission redesign replaces this hook.
