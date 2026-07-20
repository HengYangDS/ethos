## Why

`work/history-residue-closeout-root-20260719` is a clean linked Work Lane with
no active lease and an exact head already in accepted history.  It consumes a
branch and worktree but cannot be removed through ordinary holder-bound
retirement because its original holder is not active.  Treating missing lease
state as deletion authority would be unsafe; retaining an already absorbed
residue indefinitely is wasteful.

## What Changes

- Bind one exact source ref/head, its clean linked observation, and its
  accepted-ancestor relation to current Chronicle and Claim evidence.
- Permit one source-only native `lane_resolution/retire` after this carrier's
  own proof, land, and local closeout.
- Require fresh re-observation, break-glass, irreversible confirmation, and a
  receipt; make no preservation package because the source is clean.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=ownerless-landed-residual-retirement;
  reuse=extend; change=modify; facet:lifecycle=retirement;
  facet:surface=openspec,claim,chronicle,docs;
  facet:authority=source,graph,evidence,native-command.

## Out Of Scope

- Retiring a second lane from this carrier.
- Merging/rebasing historical work, raw Git or SQLite deletion, lease takeover,
  batch pruning, remote mutation, hosted CI, and preservation-package clearing.
