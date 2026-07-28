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
- DR-0003 depends on DR-0001 for proof/evidence placement. Its documentation-routing references now resolve through the Docs Registry, not through the superseded physical topology contract.
- DR-0004 depended on DR-0001 for generated-output separation and is retained only as historical context. Its fixed-path adopter requirement is superseded by the portable Docs Registry contract and ETHOS repository self-audit.
- Future decisions that alter generated artifact placement, adopter-specific
  product roots, or rollback evidence must cite DR-0001.
- Future decisions that alter portable docs metadata, taxonomy, visible sections, command examples, or plan discoverability must cite the Docs Registry contract. Decisions that alter ETHOS's own physical documentation shape must cite the ETHOS repository self-audit owner.
- Future decisions that alter proof scope compatibility, host-probe flags, or adopter proof command surfaces must cite DR-0003.
- DR-0006 depends on DR-0005 for the declarative lifecycle spine that hosts proof/evidence contracts.
- Future decisions that alter the proof trust boundary, local-vs-enforcement assurance semantics, or the independent-identity verification plug (local daemon or hosted forge) must cite DR-0006.
- DR-0007 is superseded historical context; adopter parity and documentation
  health remain separate profile-scoped concerns.
- DR-0008 is superseded; the terminal design owns direct source measurement and
  the hard repository ELOC limits without a private vector runtime.

See also: [Decision Index](decision-index.md).
