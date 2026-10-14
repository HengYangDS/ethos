## Why

On 2026-10-14 a peer's `ethos lane refresh-base --apply` rebased its lane, then had its branch update rejected with `git_effect_cas_rejected`. The compensating re-attach was also refused, which left the lane detached. Two defects made this worse than a clean refusal:

- The rebase strategy starts rewriting before it checks that this repository's write admission is armed. The merge strategy of the same command already refuses first when the hook runtime binding reports gaps.
- The refusal report keeps only the code `git_effect_cas_rejected`. The native process evidence, including the rejecting hook's or Git's stderr and the post-observation, is dropped, so the cause of the rejection could not be determined afterwards.

## What Changes

- A rebase refresh that would change the lane checks the hook runtime binding first. When write admission is not armed, it blocks with the binding's gaps and continuation before any rebase or ref effect.
- A refresh whose ref or worktree effect is refused reports the native process failure evidence alongside its existing gaps.

## Impact

- Code: `src/ethos/adapters/mutation/lane_lifecycle/work_lane_refresh.py`.
- Tests: a new refresh admission test module; the existing refresh recovery tests stub the binding as armed.
- Specs: command-plane gains one requirement for refresh admission and failure evidence.
- Unchanged: re-attaching a lane left detached after a failed compensation still needs the operator to switch back. No pending refresh record exists to identify the branch natively.
