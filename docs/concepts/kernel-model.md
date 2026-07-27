---
subject: ethos:kernel
role: explanation
state: projection
relations:
  projects: ../governance/product-design-contract.md#semantic-kernel
---

# Semantic Kernel

Design status: projection.

Purpose: give a short reader explanation of the canonical semantic model.

Canonical owner: [Product Design Contract](../governance/product-design-contract.md#semantic-kernel).

```text
(ChangeContract, RepositoryFacts, prior Attestations) -> PlanIR -> new Attestations
```

ChangeContract and Attestation are the persistent semantic entities;
RepositoryFacts is freshly observed and PlanIR is transient. Acceptance
propositions live inside the effective ChangeContract or an Attestation, and
historical views are derived projections rather than entities or truth stores.

Model Promotion remains the named conflict adjudication defined by the
[canonical owner](../governance/product-design-contract.md#model-promotion). This
projection does not restate its procedure or assert runtime effect and retirement
enforcement.
