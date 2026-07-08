---
subject: docs:root
role: index
state: canonical
relations:
  canonical_for: documentation navigation
---

# ETHOS Documentation Root

Status: canonical.

Purpose: route ETHOS product documentation through the same governed semantic
docs kernel that adopter repositories use: first-run workflows, governance,
durable decisions, dated evidence, plans, stable references, and history.

See also: [Product Index](index.md), [Quickstart](start/quickstart.md),
[Governance Docs](governance/README.md), [Decision Records](decisions/README.md),
[Evidence Docs](evidence/README.md), [Reference Docs](reference/README.md), and
[Docs Topology](architecture/docs-topology.md).

## Semantic Lanes

| Lane | Owns |
| --- | --- |
| `start/` | First-run workflows and operator entrypoints. |
| `governance/` | Policies, rules, operating constraints, and ETHOS boundary. |
| `decisions/` | Durable rulings with explicit scope and revisit trigger. |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `plans/` | Planned work and roadmap material with explicit front matter state. |
| `reference/` | Stable vocabulary, boundaries, and governance references. |
| `history/` | Retired rationale and archival logs. |

Truth state is document metadata, not path topology. Use front matter such as
`state: canonical`, `state: active`, `state: planned`, `state: superseded`, or
`state: archived` to express lifecycle. Do not create `current/` or `future/`
documentation roots.

The required kernel is the same for single repositories, monorepos, and
multi-repository governed subjects. Product-specific roots such as
`architecture/`, `concepts/`, `research/`, and `_meta/` are ETHOS product
extensions. They do not replace the common semantic kernel required across
governed repositories.
