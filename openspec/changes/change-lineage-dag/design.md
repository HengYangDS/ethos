## Context

See `proposal.md`. The canonical Commitment contract already exposes a sorted
`predecessors` tuple, while lifecycle producers and consumers assume exactly one
predecessor. Git history supplies immutable observation boundaries; Commitment
digests supply node identity. The missing owner is exact-tree resolution of
those identities before lifecycle effects.

## Goals / Non-Goals

**Goals:**

- Preserve the true partial order of governed Changes, including forks and
  joins.
- Resolve every predecessor from the exact base Git tree before mutation.
- Bind one canonical predecessor set through preflight, mutation, recovery, and
  Attestation.
- Remove singleton assumptions while retaining one semantic owner and local
  exact-CAS integration boundaries.

**Non-Goals:**

- A graph database, mutable successor index, scheduler, task graph, or new
  durable state.
- Treating `dependencies` as lineage or inferring execution readiness from
  predecessors.
- Scanning mutable worktree bytes or all historical commits during admission.

## Decisions

### Lineage is a backward-linked content-addressed DAG

Each Commitment records only its canonical predecessor digest set. Historical
Commitments remain immutable. Successors and graph views are derived by reading
Commitments from Git objects; no predecessor is backpatched and no parallel
index becomes truth.

This is a DAG by construction when every edge must resolve to a Commitment in
the exact base tree before the new Commitment is materialized. The target node
does not yet exist in that tree, so a self-edge or cycle cannot be admitted.

Alternative rejected: store both predecessors and successors. Back-links would
require rewriting historical nodes or a mutable graph ledger and create a
second authority.

### Exact-tree resolution has one semantic owner

The OpenSpec `change_lineage` adapter builds the finite set of valid active and
archived Commitment carriers in one exact tree and resolves digest membership
there. `Commitment` itself remains the sole owner of canonical digest-set
validation; the adapter adds only the request-specific rule that the current
Lease-bound Commitment is mandatory and cannot be repeated explicitly. Fresh
lane start and in-lane rollover consume those owners rather than introducing a
second collection algebra. Mutable filesystem scans, cache databases, and
branch-wide history search are not authoritative inputs.

Alternative rejected: each lifecycle command implements its own carrier scan.
That would let producer, recovery, and verifier disagree about the same edge.

### In-lane rollover preserves the current predecessor mandatorily

`lane start-change` accepts repeatable `--predecessor <digest>` values as
additional lineage. The current Lease-bound Commitment digest is always
included, regardless of caller input, then the full set is canonicalized by the
Commitment contract. The caller cannot omit its actual lineage or substitute an
unrelated parent.

Fresh `lane start --commitment` may carry historical predecessors because it
has no current lane parent. Every declared digest must resolve at the exact
accepted/candidate base before any Git ref, worktree, or Lease effect.

Alternative rejected: require all successors to be created inside one existing
lane. That would serialize independent forks and make greenfield or recovered
lineage unnecessarily stateful.

### The complete set is effect identity

The prepared rollover request records the complete predecessor set. Recovery
recomputes the successor Commitment and accepts only exact set equality. The
start-effect Attestation requires the old Lease-bound digest to be a member and
binds the successor Commitment digest, which already covers every predecessor.

Alternative rejected: validate only membership of the old digest. Membership
alone preserves local authority but would allow retry to add or remove another
parent without changing the recognized request.

### Lineage and execution dependencies stay separate

`predecessors` answer which governed Changes this Change semantically descends
from. `dependencies` answer which independently named obligations constrain
execution. Concurrency remains selected by satisfied dependencies, disjoint
scope/effects, and per-ref exact CAS; lineage does not impose a global total
order.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `contracts:Commitment v2 identity is explicit and bounded` | `2.1` | existing Commitment digest-set validation plus public fork/join and ambiguous-request tests |
| `command-plane:Start Change accepts explicit predecessor identities` | `2.2` | public CLI multi-predecessor rollover test |
| `repository-governance:Change creation resolves lineage before effects` | `2.3` | fresh lane unresolved-predecessor no-effect test |
| `repository-governance:Change start recovery preserves exact lineage` | `2.4` | prepared/recovery predecessor-set drift test |
| `repository-governance:Change lineage permits concurrency without global serialization` | `2.3` | fork construction plus independent fresh-lane dry-runs from one predecessor without shared mutable lineage state |

## Risks / Trade-offs

- [Risk] Repository-wide carrier enumeration adds latency → inspect only
  canonical active/archive Commitment paths in one exact tree and parse each
  object once per operation.
- [Risk] Duplicate or noncanonical predecessor input creates inconsistent
  identity → use the existing Commitment canonical digest-set validator and
  reject noncanonical carrier bytes.
- [Risk] Lineage is mistaken for execution order → keep the fields, validation,
  CLI wording, specs, and tests distinct.
- [Risk] Retry recognizes a different join → bind and compare the entire
  predecessor tuple in the prepared request and recovered post-image.

## Migration Plan

1. Add real public-flow tests that fail on the existing singleton behavior.
2. Add exact-tree predecessor resolution to the OpenSpec Change-lineage owner.
3. Thread the canonical set through fresh start, rollover, recovery, and
   Attestation; delete singleton-only branches and parameters.
4. Prove repository-wide reference closure, strict OpenSpec validation,
   focused gates, full proof, archive, land, and owner-lane retirement.
