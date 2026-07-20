## Why

`work/skill-scripts-ruff-20260719` is a linked, dirty, lease-free source whose
committed head is already accepted. Its useful uncommitted behavior is limited
to current Ruff compliance in four repository-local skill scripts. Leaving the
source untouched retains both a stale worktree and quality debt; raw deletion
or a historical merge would either lose recovery material or reintroduce stale
quality semantics.

## What Changes

- Absorb only the current-compatible output-routing behavior in four skill
  scripts and refresh their package digests.
- Bind one exact dirty source to later native `lane_resolution/preserve-retire`.
- Require current proof, candidate land, accepted closeout, fresh observation,
  preservation, break-glass, and irreversible confirmation before source-only
  retirement.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=ownerless-skill-scripts-semantic-closeout;
  reuse=extend; change=modify; facet:lifecycle=absorption,retirement;
  facet:surface=skills,quality,openspec,claim,chronicle,docs;
  facet:authority=source,test,evidence,native-command.

## Out Of Scope

- Whole-branch merge/rebase, any lane other than the named source, raw
  deletion, lease takeover, candidate train repair, remote mutation, hosted CI,
  or publication.
