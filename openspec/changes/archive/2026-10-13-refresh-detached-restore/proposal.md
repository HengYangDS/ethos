## Why

A refused or interrupted `ethos lane refresh-base` can leave a Work Lane detached on its rebased head with no native way back:

- After a successful rebase, the restore path compensates with `git restore --source <original>`. That moves the index and worktree but leaves `HEAD` on the rebased commit, so the compensation's own clean-status postcondition fails and the branch is never re-attached. Every refused ref update after a rebase that changed the tree ends with `refresh_base_worktree_restore_failed`. This is how a peer lane stayed detached on 2026-10-14 at 00:19.
- A refresh interrupted after its rebase, for example by a deadline, leaves no record of the branch it rewrote. A later `refresh-base --apply` finds no applied effect and reports `git_effect_recovery_ambiguous`.

## What Changes

- The refresh restore switches the detached worktree back to the original head before re-attaching the branch. The rebase failure, postcondition failure, rejected replay and refused effect paths share this one restore.
- Before rebasing, the refresh records its branch, original head and candidate head in the lane's own Git directory, and removes the record once the lane is attached again.
- On a detached lane with no applied refresh effect, `refresh-base --apply` uses that record. When the branch still holds the recorded head, the lane is clean and no rebase is unfinished, it restores the lane and reports `base_restored` with the exact refresh as its next action. Otherwise it still blocks.

## Impact

- Code: `src/ethos/adapters/mutation/lane_lifecycle/work_lane_refresh.py` and a new `work_lane_refresh_record.py`.
- Tests: a new real-Git restore test module; the existing refresh recovery tests stub the record.
- Specs: command-plane gains one requirement for restoring refused and interrupted refreshes.
