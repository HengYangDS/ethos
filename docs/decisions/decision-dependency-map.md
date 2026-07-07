---
subject: ethos:decisions:dependency-map
role: reference
state: canonical
relations:
  canonical_for: decision dependency map
---

# Decision Dependency Map

Status: canonical.

Purpose: show dependencies between ETHOS durable rulings.

- DR-0001 currently has no prior ETHOS Decision Record dependency.
- DR-0002 depends on DR-0001 for evidence/current/future/generated-output separation.
- Future decisions that alter generated artifact placement, adopter-specific
  product roots, or rollback evidence must cite DR-0001.
- Future decisions that alter documentation lane topology, decision-record routing, or adopter docs isomorphism must cite DR-0002.

See also: [Decision Index](decision-index.md).
