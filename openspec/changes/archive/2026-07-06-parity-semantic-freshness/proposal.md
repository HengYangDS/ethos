## Why

Tracked parity evidence can stale itself: the shadow run records the current
commit, then writing and committing the evidence changes HEAD. Requiring the
recorded evidence to name the final commit creates a fixed-point problem and
keeps `ethos report` in a parity-pending state even when the product semantic
state did not change after the shadow run.

## What Changes

- Record parity-relevant semantic tree digests in tracked shadow evidence.
- Validate freshness by HEAD equivalence or by matching semantic digest over the
  parity-relevant path set.
- Keep HEAD binding visible in provenance while distinguishing commit-object
  freshness from semantic-tree freshness.
- Keep the parity-relevant path list as one source of truth in the parity module.

## Capabilities

- `ethos-repository`: subject=parity-evidence-freshness; reuse=extend; change=modify; facet:lifecycle=validation,runtime; facet:surface=cli,docs,openspec,test,evidence; facet:authority=source,test,docs,openspec,evidence

## Out Of Scope

- No weakening of parity evidence when source, contracts, OpenSpec, claims,
  rules, skills, or governance docs change.
- No new truth store.
- No remote publication or hosted CI claim.
