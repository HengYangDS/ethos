## Why

Repository effects currently have several owners. `git_effects` performs exact
ref CAS and issues effect Attestations, while the reference-transaction hook
also advances Lease state and lifecycle modules own separate compensation and
recovery paths. Real Git proves that porcelain merge and checkout can project
index/worktree changes before the ref hook may reject the ref, so hook admission
alone cannot make the repository transition atomic.

## What Changes

- Make one TransitionPlan-bound executor own admission, exact local ref CAS,
  post-observation, effect Attestation persistence, compensation, and recovery.
- Treat ref intent as the executor's short-lived exact capability; hooks may
  validate it and observe completion but may not advance Lease or mint effect
  state.
- Restore rejected raw Git checkout projections only when the post-failure
  index and worktree prove the exact rejected target; otherwise fail visibly
  without guessing.
- Delete lifecycle-specific ref effect and recovery owners after their unique
  semantics are migrated.

## Out of Scope

Remote publication, generic unbound-lane disposition, runtime activation, and
OpenSpec filesystem/archive orchestration remain successor effect adapters.
