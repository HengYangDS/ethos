## Why

`work/artifact-topology-hotpath-20260714` survived as a registered detached
worktree at an accepted ancestor with four unique dirty files and no valid
owner.  Raw cleanup would lose recoverable bytes; replaying the historical
implementation would restore superseded cache state and weaker evidence
granularity.

## What Changes

- Bind the exact source head, normalized branch, dirty paths, and patch digest.
- Record which useful semantics current accepted source already owns and which
  historical behavior is explicitly rejected.
- Permit one later native `lane_resolution/preserve-retire` transition only
  after this carrier is proven, landed, and locally closed out.
- Keep package clearing separate and exact-manifest-bound.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=detached-ownerless-residue-normalization;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,retirement;
  facet:surface=openspec,claim,chronicle,docs;
  facet:authority=git,evidence,test,native-command.

## Out Of Scope

- Replaying the historical implementation, changing product source, batch
  cleanup, valid-owner takeover, broad worktree prune, raw ref deletion, remote
  publication, hosted claims, or clearing a package before a later exact
  manifest decision.
