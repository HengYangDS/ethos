## Context

`refresh_work_lane_base` runs `git rebase` and then applies the lane ref update through `execute_git_effect`. If the update is refused, it compensates the worktree and re-attaches the branch. The merge strategy calls `hook_runtime_binding` before any effect and fails on its required gaps. The rebase strategy does not.

`execute_git_effect` raises a `GitExecutionError` whose evidence contains the native exit, stderr and post-observation. The refresh failure path keeps only `str(error)`.

## Decisions

1. Check write admission only when the lane actually needs a refresh. A lane that already contains the candidate keeps reporting `base_current` without depending on the hook runtime.
2. Use the binding's own `next_action` as the continuation, which is normally the hook install that re-arms admission.
3. Carry `process_failure` evidence with the same shape that lane retirement already reports for process failures.
4. Native recovery of a detached lane needs a durable pending-refresh record that names its branch. That is a separate change; this one prevents the refusal from starting and keeps its cause diagnosable.
