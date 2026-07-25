# OpenSpec Capability Specs

Accepted capability specs describe current ETHOS product behavior. Each
capability directory contains:

- `spec.md`: official OpenSpec requirements and scenarios.
- `capability.toml`: ETHOS routing and proof metadata for proposal review.

Capability directory names are semantic IDs, not Python packages, command names,
host surfaces, or vendor roles. They are deliberately stable across package
layout changes and implementation refactors.

## Canonical Capability Set

| Capability | Family | Owner package | Boundary |
| --- | --- | --- | --- |
| `kernel` | `kernel` | `ethos` | Kernel chain, result envelope, PlanIR. |
| `contracts` | `contracts` | `ethos-core` | Schemas, TOML contracts, command JSON, evidence envelopes. |
| `repository-governance` | `repository-governance` | `ethos` | Git-native lifecycle, Work Lanes, claims, evidence, chronicle, evolution. |
| `adapters` | `adapters` | `ethos` | Git, process, OpenSpec, hosted CI, MCP, and host protocol adapters. |
| `command-plane` | `surfaces` | `ethos` | Public transition and reader commands. |
| `assistant-projections` | `surfaces` | `ethos` | Skills, agent context, assistant and host projections. |
| `distribution` | `surfaces` | `ethos` | Launchers, package-manager and distribution surfaces. |
| `quality` | `quality` | `ethos-core` | Quality policy, deterministic proof, docs profile, gate descriptors. |
| `proof-hosts` | `proof` | `ethos` | Conformance, fixtures, parity, replay, sample repositories. |

This set is MECE by primary invariant. A change that touches multiple
capabilities names each affected semantic boundary explicitly; it does not create
package-shaped specs to mirror implementation directories.

## Capability Profile Duties

A profile records:

- `family`: a human-scale family from `families.toml`.
- `owner.package` and `owner.scope`: implementation owner boundary, not the
  capability identity.
- `primary_invariant`: the one behavior the capability protects.
- `routing_question`: the question that selects this capability over peers.
- `decision_axes`: facets useful for routing, proof, and review.
- `recommended_facets`: local hints for proposal metadata.
- `boundary_rules`: what this capability must not absorb.
- `proof_profile`: default proof, executed proof, and required gates.

See `capability.template.toml` for the scaffold shape.
