## Context

The official OpenSpec boundary is the promoted `ethos-repository` capability.
The product boundary is tracked shadow parity evidence under `evidence/parity/`
and the `ethos report` parity scorecard.

## Design

Parity evidence now carries two freshness witnesses:

1. `product_head` / `target_head`: the commit where the shadow comparison ran.
2. `product_semantic_sha256` / `target_semantic_sha256`: a digest of Git tree
   entries under the parity-relevant path set.

Validation accepts the evidence when the head matches, when an existing
acceptable-head rule proves path equivalence, or when the semantic digest still
matches the current parity-relevant tree. A commit that only records the evidence
can therefore become the accepted root without making that evidence stale. A
later commit that changes source, system contracts, OpenSpec, claims, rules,
skills, workspace policy, lockfiles, or governance docs changes the semantic
digest and reopens the parity gap.

This preserves the kernel distinction: evidence is still evidence, but freshness
is measured at the boundary that can actually move the parity verdict. No host,
message bus, or generated projection becomes a truth center.

## Alternatives

- Keep refreshing parity after every commit: rejected because tracked evidence
  cannot pre-bind to the commit that includes itself.
- Accept any parent HEAD: rejected because it can mask real semantic changes.
- Remove parity from `report`: rejected because parity is a small signal for
  migration and adopter equivalence.

## Proof Strategy

- Unit tests prove self-evidence commits remain fresh by semantic digest and
  later product-source commits stale the same evidence.
- Existing parity tests prove parent/equivalent-head behavior remains intact.
- `ethos report --json` must show `parity_pending_count=0` after refreshed
  evidence.
- Full tests, lint, schemas, OpenSpec, claims, and executed proof bind the change
  before land.
