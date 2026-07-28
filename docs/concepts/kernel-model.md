---
subject: ethos:kernel
role: explanation
state: active
relations:
  projects: ../governance/product-design-contract.md#semantic-kernel
---

# Semantic Kernel

Status: active projection.

Purpose: give a short reader explanation of the canonical semantic model.

Canonical owner: [Product Design Contract](../governance/product-design-contract.md#semantic-kernel).

See also: [Command Plane](../reference/command-plane.md) and
[Glossary](../reference/glossary.md).

```text
(Commitment, Facts, prior Attestations) -> TransitionPlan -> new Attestations
```

Commitment and Attestation are the persistent semantic entities;
Facts is freshly observed and TransitionPlan is transient. Acceptance
propositions live inside the effective Commitment or an Attestation, and
historical views are derived projections rather than entities or truth stores.

Model Promotion remains the named conflict adjudication defined by the
[canonical owner](../governance/product-design-contract.md#model-promotion). This
projection does not restate its procedure or assert runtime effect and retirement
enforcement.
