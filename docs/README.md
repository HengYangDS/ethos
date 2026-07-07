---
subject: docs:root
role: index
state: canonical
relations:
  canonical_for: documentation navigation
---

# ETHOS Documentation Root

Status: canonical.

Purpose: route ETHOS product documentation through the same governed docs kernel
that adopter repositories use: current contracts, durable decisions, dated
evidence, future designs, stable references, and history.

See also: [Product Index](index.md), [Current Docs](current/README.md),
[Decision Records](decisions/README.md), [Evidence Docs](evidence/README.md),
[Reference Docs](reference/README.md), and [Docs Topology](architecture/docs-topology.md).

## Lanes

| Lane | Owns |
| --- | --- |
| `current/` | Implemented contracts, runbooks, and development rules. |
| `decisions/` | Durable rulings with explicit scope and revisit trigger. |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `future/` | Target designs and roadmap material not yet current truth. |
| `reference/` | Stable vocabulary, boundaries, and governance references. |
| `history/` | Retired rationale and archival logs. |

The required kernel is the same for single repositories, monorepos, and
multi-repository governed subjects. Product-specific roots such as
`architecture/`, `governance/`, `concepts/`, `start/`, `plans/`, and
`research/` are ETHOS product extensions. They do not
replace the common kernel required across governed repositories.
