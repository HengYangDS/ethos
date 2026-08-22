## Why

ETHOS already models `Commitment.predecessors` as a set, but fresh lane start,
in-lane Change rollover, recovery, and Attestation admission still impose a
single-predecessor path. That accidental total order prevents truthful fork and
join lineage, creates unnecessary serialization, and lets retry identity omit
part of the governed Change ancestry.

## What Changes

- Define governed Change lineage as an immutable, backward-linked DAG derived
  from content-addressed Commitment carriers in an exact Git tree.
- Allow one historical Commitment to have several successors and one successor
  Commitment to name several predecessors.
- Require in-lane `start-change` to include the current Lease-bound Commitment
  while accepting additional explicit predecessor digests.
- Allow fresh lane start with historical predecessors only when every digest
  resolves in the exact base tree, before any ref, worktree, or Lease effect.
- Bind the complete canonical predecessor set into request, recovery, effect,
  and Attestation identity; reject set drift rather than accepting a partial
  lineage match.
- Keep execution dependencies distinct from lineage and delete singleton-only
  checks without adding a graph database, successor back-links, or another
  lifecycle state machine.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contracts`: Commitment lineage is a canonical predecessor DAG rather than a
  singleton successor link.
- `command-plane`: public Change start accepts repeatable predecessor identity
  and projects exact fail-fast lineage errors.
- `repository-governance`: fresh and in-lane Change creation resolve immutable
  predecessor identities from exact Git facts and preserve them through
  recovery and Attestation.

## Impact

- Commitment loading and exact-tree lineage resolution.
- Fresh Work Lane preflight and in-lane Change rollover.
- Start-change CLI, prepared request, recovery, and generated Attestation.
- Focused real-repository tests for fork, join, unresolved edges, and retry
  drift.

Out of scope: execution dependency scheduling, a graph index or ledger,
historical Commitment mutation, successor fields, global workflow ordering, or
changes to Git's per-ref exact-CAS serialization.
