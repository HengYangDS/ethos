## Why

Configured generic parity evidence is a candidate-facing product proof, while
candidate and accepted checkouts intentionally reject tracked writes. The old
lifecycle projection told operators to refresh the evidence after candidate
landing, but an ambient self-governance unit assertion required that same
evidence to be current before the Work Lane could prove. The result was a
self-created deadlock rather than a legitimate ownership boundary.

## What Changes

- Make stale configured generic parity evidence an explicit
  `quality evidence-freshness` proof gap.
- Define the only valid order: source commit -> Work-Lane parity refresh ->
  evidence commit -> executed proof -> candidate land.
- Remove the ambient live-repository unit assertion that hid this lifecycle
  requirement inside the architecture suite.
- Return the Work-Lane pre-proof ownership and commit boundary in the refresh
  package and update the lifecycle projection.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=parity-evidence-transaction;
  reuse=extend; change=modify; facet:lifecycle=proof,land;
  facet:surface=quality,parity; facet:evidence=freshness,parity;
  facet:authority=work-lane,candidate.

## Out Of Scope

- Allowing direct tracked writes in candidate or accepted roots.
- Weakening semantic parity freshness or treating stale parity as advisory.
- Mutating, landing, or retiring any foreign Work Lane.

## Impact

The repair adds no new authority and no new workflow engine. It moves an
existing hard requirement to the evidence-freshness gate that owns it and makes
the pre-proof transaction order observable to humans and agents.
