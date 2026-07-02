# OpenSpec Capability Specs

Accepted capability specs describe current ETHOS product behavior. Each
capability directory contains:

- `spec.md`: official OpenSpec requirements and scenarios.
- `capability.toml`: ETHOS routing and proof metadata for proposal review.

Capability names are live routing identifiers. Proposal capability entries must
name these directories exactly; aliases are diagnostic migration aids only and
must not become routing truth.

## Capability Profile Duties

A profile records:

- `family`: a human-scale family from `families.toml`.
- `owner.package` and `owner.scope`: product owner boundary.
- `primary_invariant`: the one behavior the capability protects.
- `routing_question`: the question that selects this capability over peers.
- `decision_axes`: facets useful for routing, proof, and review.
- `recommended_facets`: local hints for proposal metadata.
- `boundary_rules`: what this capability must not absorb.
- `proof_profile`: default proof, executed proof, and required gates.

See `capability.template.toml` for the scaffold shape.
