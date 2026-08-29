## Why

Repository effects currently have several owners because the repository model
duplicates facts and intent before execution begins. Tracked
`commitment.toml` files repeat official OpenSpec, Lease payloads mirror moving
Git coordinates and Commitment bytes, and predecessor/successor plus
hypothesis/experiment fields turn history and design work into parallel runtime
authority. `git_effects` then performs exact ref CAS while hooks and lifecycle
modules separately advance those duplicated states and own compensation or
recovery paths.

Real Git also proves that porcelain merge and checkout can project
index/worktree changes before the ref hook may reject the ref. Hook admission
alone cannot make the repository transition atomic, and synchronizing more
copies of the same facts cannot repair that boundary.

## What Changes

- Make one TransitionPlan-bound executor own admission, exact local ref CAS,
  post-observation, effect Attestation persistence, compensation, and recovery.
- Make official OpenSpec the only tracked intent carrier and compile the minimal
  immutable Commitment value from one exact official projection.
- Reduce Lease to the expiring CAS relation between one lane incarnation and
  one holder; read HEAD, tree, index, changed paths, and selected intent from
  fresh facts at admission and effect time.
- Delete persisted predecessor/successor lineage. Derive ordinary history from
  Git and archived OpenSpec; bind only an admission-relevant prior Attestation
  as an exact TransitionPlan input.
- Delete Commitment hypothesis, falsifier, and experiment-protocol fields.
  OpenSpec design/spec/tasks own proposals and procedures; Attestations own
  exact observations and conclusions.
- Treat ref intent as the executor's short-lived exact capability; hooks may
  validate it and observe completion but may not advance Lease or mint effect
  state.
- Restore rejected raw Git checkout projections only when the post-failure
  index and worktree prove the exact rejected target; otherwise fail visibly
  without guessing.
- Delete tracked Commitment carriers, private commitment-rebind and successor
  lineage machinery, and lifecycle-specific ref effect/recovery owners after
  their unique acceptance or CAS semantics are migrated.

## Out of Scope

Remote publication, generic unbound-lane disposition, runtime activation, and
OpenSpec filesystem/archive projection remain later effect adapters. They may
not reintroduce a tracked intent carrier, lineage ledger, experiment state
machine, or Lease payload mirror.
