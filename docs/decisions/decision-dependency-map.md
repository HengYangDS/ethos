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
- DR-0002 depends on DR-0001 for evidence/semantic-docs/plans/generated-output separation, and is superseded by DR-0004.
- DR-0003 depends on DR-0001 for proof/evidence placement and on DR-0004 for adopter-facing command documentation routing.
- DR-0004 depends on DR-0001 for generated-output separation and supersedes DR-0002 for documentation topology.
- Future decisions that alter generated artifact placement, adopter-specific
  product roots, or rollback evidence must cite DR-0001.
- Future decisions that alter documentation topology, decision-record routing, or adopter docs kernel requirements must cite DR-0004.
- Future decisions that alter proof scope compatibility, host-probe flags, or adopter proof command surfaces must cite DR-0003.
- DR-0006 depends on DR-0005 for the declarative runtime spine that hosts proof/evidence contracts.
- Future decisions that alter the proof trust boundary, the local-vs-enforcement claim semantics, or the independent-identity verification plug (local daemon or hosted forge) must cite DR-0006.
- DR-0007 is superseded: DR-0004 v2 owns strict docs-topology semantics, while
  the Product Design Contract and Capability Parity Ledger own the locus of
  external-adopter parity evidence.
- DR-0008 is superseded; the terminal design owns direct source measurement and
  the hard repository ELOC limits without a private vector runtime.

See also: [Decision Index](decision-index.md).
