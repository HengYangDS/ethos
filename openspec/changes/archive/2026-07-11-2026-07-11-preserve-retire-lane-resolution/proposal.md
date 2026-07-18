# preserve-retire-lane-resolution

## Why

An owner-unknown Work Lane can contain uncommitted or untracked work. Existing
`preserve` retains that work but cannot converge the lane, while `retire`
correctly refuses a dirty lane. Operators then face an unsafe manual-deletion
gap after preservation.

## What Changes

- Add the exceptional `preserve-retire` resolution disposition.
- Require accepted Chronicle evidence, `--break-glass`, exact observation
  recomputation, and `--confirm-irreversible`.
- Create and verify the recovery bundle, patch, archive, and manifest before
  removing the precise branch and linked worktree.
- Keep `preserve` non-destructive and ordinary dirty `retire` fail-closed.

## Capabilities

- `repository-governance`: subject=preserve-retire-lane-resolution;
  reuse=extend; change=modify; facet:lifecycle=work-lane-resolution,
  preservation,retirement; facet:surface=cli,docs,openspec,test;
  facet:authority=source,test,docs,chronicle

## Out of Scope

- No remote Git operation, hosted CI claim, or publication.
- No retirement of an actively leased lane without a subsequent exact decision.
