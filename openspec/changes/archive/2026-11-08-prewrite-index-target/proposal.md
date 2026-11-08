# Proposal

## Why

A selective staging patch can match the index while not matching the working
file. Native prewrite needs to evaluate that exact index postimage without
requiring an adopter staging controller or consuming unrelated working content.

## What Changes

- Add `--target index` to the existing `lane prewrite --patch` request; preserve
  the worktree default and the existing staged admission owner.
- Check the exact patch with native `git apply --cached --check`, bind the
  observed index tree and exact preimage, and refuse stale observations.
- Preserve working files and every other staged path; keep preview separate
  from the actual staging effect and its fresh admission.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: exact index-target prewrite admission.

## Impact

Only prewrite patch admission, its lane CLI target flag and directly affected
regressions implement this seam. Root catalog, hooks, paradigm policy, runtime
selection, publication and adopter mutation are not implementation scope.
No dependency, staging executor, durable permit or second controller is added.
