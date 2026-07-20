## Why

`work/adopter-openspec-lifecycle-continuity-20260719` is a clean linked Work
Lane with no active lease and an exact head already in accepted history. It
retains historical continuity evidence but no unique operational work; leaving
it open would preserve a duplicate worktree/ref rather than useful semantics.
Missing lease state is not deletion authority.

## What Changes

- Bind one exact source ref/head, clean linked observation, accepted-ancestor
  relation, and graph-backed absorption basis to a current Claim and Chronicle.
- Permit one source-only native `lane_resolution/retire` only after this carrier
  completes normal proof, local closeout, and fresh re-observation.
- Require break-glass, irreversible confirmation, and a receipt; no
  preservation package is created because the source is clean.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=ownerless-adopter-openspec-continuity-retirement;
  reuse=extend; change=modify; facet:lifecycle=retirement;
  facet:surface=openspec,claim,chronicle,docs;
  facet:authority=source,graph,evidence,native-command.

## Out Of Scope

- Retiring another lane or the predecessor adopter lane.
- Whole-branch merge/rebase, raw Git or SQLite deletion, lease takeover, batch
  pruning, remote mutation, hosted CI, or preservation-package clearing.
