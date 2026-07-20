## Why

`work/artifact-topology-hotpath-repair-20260714` is a linked, dirty,
missing-lease Work Lane. Its useful artifact-topology behavior has been evolved
by current accepted contracts, but neither path overlap nor its retained bundle
proves semantic absorption. Leaving it forever retains an unnecessary active
worktree; deleting it now would destroy recoverable dirty state without a
current semantic judgment.

## What Changes

- Bind one exact source ref/head and staged parity patch to a current accepted
  artifact-topology semantic review.
- Bind focused current topology and CEL proof to a later one-source native
  `lane_resolution/preserve-retire` transition.
- Retain the preservation package after retirement; require a separate
  manifest-bound `clear-preservation` authority only if no unique behavior
  remains.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=artifact-topology-ownerless-semantic-absorption;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,retirement;
  facet:surface=openspec,claim,chronicle,docs; facet:authority=source,test,openspec,evidence,native-command.

## Out Of Scope

- Merging or rebasing the historical source lane.
- Batch orphan cleanup, foreign lease takeover, raw deletion, broad worktree
  prune, remote publication, GitHub/GitLab mutation, hosted CI, or package
  clearing.
