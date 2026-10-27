---
subject: ethos:fleet-adopters
role: explanation
state: canonical
relations:
  canonical_for: external repository governance
---

# Adopters

Status: canonical.

Purpose: define how ETHOS governs one external repository without creating a
second command plane or a central adopter task store.

See also: [Adoption Profiles](adoption-profiles.md) and the
[repository-governance specification](../../openspec/specs/repository-governance/spec.md), whose "Repository profile is a strict
current binding" owns the binding.

ETHOS governs a repository through one explicit binding and its declared
profile. Profiles choose repository facts, adapters, and proof depth; they do
not change the public command meanings.

```bash
ethos adopt --root <repo> --json
ethos status --root <repo> --json
ethos prove --root <repo> --execute --full --expect-head <HEAD> --json
```

Adopter proof lives in that repository's own Attestation set (adapters "Attestations use one
deterministic Git set carrier"). Provider state, editor state, and generated projections are
adapters; they support an adopter claim only once promoted into source, tests, schemas, docs,
OpenSpec, or Attestations.

An adopter may also serve as a reference integration, a dogfood repository, a migration
oracle or a rollback anchor. None of these roles makes it product ontology
([Isomorphic Adopter Governance](../governance/product-design-contract.md#isomorphic-adopter-governance)).

## Moving An Adopter To A New Execution Substrate

A replacement execution substrate takes over an adopter's governance only when it is no weaker
than the incumbent. Four repository-governance requirements state the contract: "A replacement
execution substrate is no weaker than its incumbent", "A comparative correction rests on evidence
outside the candidate", "A retirement judgment authorizes substrate effects" and "Comparative
proof refuses weakened evidence". [DR-0014](../decisions/dr-0014-comparative-correction.md)
records why a correction must rest on evidence from outside the candidate. Until a comparative
checker exists, the retirement judgment records each comparison and correction, and review
verifies them.
