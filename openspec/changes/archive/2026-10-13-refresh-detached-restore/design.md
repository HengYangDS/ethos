## Context

`_refresh_work_lane` rebases the lane head onto the candidate head as a detached commit, validates the replayed commits, then updates the lane branch through `execute_git_effect` and re-attaches it with `attach_worktree`. `attach_worktree` only switches a detached worktree whose index tree equals the branch head's tree. The current restore calls `compensate_git_worktree`, which restores the index and worktree to the original tree but keeps `HEAD` on the rebased commit, so its clean-status check fails before the re-attach.

The ref intents that `execute_git_effect` writes live for one minute and are removed on abort, so they cannot name the branch of an interrupted refresh.

## Decisions

1. Restore with `git switch --detach <original>` and then `attach_worktree`. A refresh only starts on a clean lane and the rebase leaves it clean, so the switch moves `HEAD`, index and worktree together. After `git rebase --abort`, `HEAD` is already on the original head and the switch changes nothing.
2. Keep the pending refresh record at `git rev-parse --git-path ethos/lane-refresh.json`. Git resolves it inside the lane's private worktree directory, so it is keyed by the worktree without naming one, and it disappears when the worktree is removed.
3. Restore an interrupted refresh rather than complete it. The branch still holds the original head and the replay can be recomputed, so restoring needs no new effect evidence. The operator reruns the exact refresh.
4. Fail closed: a dirty lane, an unfinished rebase, a branch that no longer holds the recorded head or an unreadable record blocks without moving the worktree. `git rebase --abort` would discard edits made after the interruption, so the operator decides it.
