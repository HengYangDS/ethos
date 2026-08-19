## Why

ETHOS currently treats remote publication as a branch-only concern and still
retains product paths that can recreate or reconcile divergent Git objects.
That contradicts the local-first authority model, misclassifies signed release
tags as `other`, and lets the public command and pre-push hook select proof by
different rules.

## What Changes

- **BREAKING** Make one locally created and signed Git commit or annotated tag
  the sole product object; peers may transport and verify it but never replay,
  re-sign, merge, or rewrite it.
- Replace branch-only publication admission with one provider-neutral mapping
  from full ref kind to lifecycle role and allowed effect.
- Generalize the existing receipt-bound remote executor from proposal branches
  to accepted branches, release branches, proposal branches, and annotated
  release tags while preserving peer-local exact CAS and partial-effect
  receipts.
- Bind publication plans and pre-push admission to the same exact
  commit/tree/gate proof Attestation.
- Verify exact commit OID, annotated tag object OID, peeled commit, tree, and
  local signature trust after every peer effect.
- Delete same-payload identity repair and divergent-peer reconciliation as
  standing product capabilities; divergence fails closed instead of producing
  another product object.
- Keep zero, one, or many declared peers independent and optional. Transport
  authentication and Forge account presentation do not own product identity.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: Define local Git object authority, full-ref
  publication admission, exact-object peer projection, and shared proof
  consumption.
- `command-plane`: Remove public object-recreation recovery and make publish
  the sole receipt-bound Git object projection command.

## Impact

The change replaces publication contracts, ref admission, hook projection,
proof binding, and the current proposal-only executor. It deletes identity
rewrite and cross-peer reconciliation source, tests, rules, and documentation.
It does not change AIGW or Proxy, build an accepted runtime, define product
versions, repair historical remote divergence, or introduce release-asset
trust; asset signing and TUF/in-toto integration remain a separate atom.
