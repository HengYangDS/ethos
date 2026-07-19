---
subject: ethos:container-contract-current-replay
reuse: extend
change: modify
facet:lifecycle: validation
facet:surface: schema,profile,evidence,source,test,docs,openspec
facet:authority: source,test,schema,docs,openspec,claim,evidence
---

## Why

Four ownerless container-contract lanes retain a coherent but never accepted
intent: an adopter that declares container delivery obligations needs a
provider-neutral, fail-closed validation boundary.  The accepted repository has
no equivalent contract today, so deleting those lanes as stale would discard a
real product capability.  Replaying their old branches wholesale would instead
import obsolete topology and source-budget debt.

## What Changes

- Add an opt-in `container_contract` declaration to an adopter profile.
- Validate the declaration and its manifest against product-owned schemas, not
  adopter-overridable schema copies.
- Require hash-bound, tracked evidence for declared delivery and recovery
  records, required Linux architecture coverage, and explicit persistent-asset
  restore policy.
- Reject vendor-branded runtime declarations, path escapes, untracked or stale
  evidence, duplicate asset identifiers, and invalid untrusted output schemas.
- Surface this validation through the existing schema report so a declared
  contract is promotion-relevant without creating a second command plane.

## Capabilities

### Modified Capabilities

- `contracts`: subject=container-contract-current-replay; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema,profile,evidence,source,test,docs,openspec; facet:authority=source,test,schema,docs,openspec,claim,evidence

## Out Of Scope

- Publishing images, starting containers, or asserting hosted-provider success.
- Naming a preferred local container runtime or making one required.
- Adopting a concrete container contract for ETHOS itself, Alphasim, or another
  adopter repository in this change.
