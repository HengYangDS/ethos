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
- DR-0002 depends on DR-0001 for evidence/semantic-docs/plans/generated-output separation.
- DR-0003 depends on DR-0001 for proof/evidence placement and on DR-0002 for adopter-facing command documentation routing.
- Future decisions that alter generated artifact placement, adopter-specific
  product roots, or rollback evidence must cite DR-0001.
- Future decisions that alter documentation lane topology, decision-record routing, or adopter docs isomorphism must cite DR-0002.
- Future decisions that alter proof scope compatibility, host-probe flags, or adopter proof command surfaces must cite DR-0003.

See also: [Decision Index](decision-index.md).
