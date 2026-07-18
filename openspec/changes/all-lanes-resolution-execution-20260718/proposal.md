## Why

The accepted replay has closed the owned safety lane, but the local repository
still contains a changing Work Lane topology. A fresh Git/worktree audit shows
clean accepted ancestors, absorbed dirty overlays, residual semantic patches,
valid foreign leases, one diverged unbound ref, and post-freeze lanes. Previous
program policy requires a current accepted Chronicle decision before any
missing-lease exceptional effect.

## What Changes

- Promote a fresh exact Work Lane resolution matrix and a bounded Chronicle
  policy for `preserve`, `retire`, `preserve-retire`, and `block`
  dispositions.
- Extend the repository-governance specification with the already implemented
  digest-bound Chronicle-disposition scenario for native resolution decisions.
- Execute only the later native two-phase decisions that match the accepted
  matrix and fresh target observation; preserve the seven selected dirty
  residuals without retirement and leave all holder-bound or other residual
  rows explicitly blocked rather than implying absorption.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=work-lane-resolution-execution; reuse=extend;
  change=modify; facet:lifecycle=exceptional-resolution,observation,recovery,
  retirement; facet:surface=openspec,chronicle,claim,local-receipt;
  facet:authority=accepted-chronicle,exact-head,observation-digest,
  non-authoritative-receipt.

## Impact

- `docs/plans/all-lanes-resolution-execution-20260718.md`
- Topic-scoped Chronicle, claim, and exact matrix.
- Existing `repository-governance` OpenSpec requirement only; no new command,
  dependency, remote operation, or broad foreign-lane authority.

## Out of Scope

- Wholescale merging or deletion of diverged branches.
- Foreign holder takeover, remote publication, hosted CI, release distribution,
  clearing retained recovery packages, or claims of semantic absorption without
  exact evidence.
