---
subject: ethos:engineering-axioms
role: policy
state: active
relations:
  derives: ../docs/governance/product-design-contract.md#root-constraint
---

# Engineering Axioms

These are derived, machine-adjacent engineering constraints from the [Root
Constraint](../docs/governance/product-design-contract.md#root-constraint). They
do not create a second semantic owner, ontology, or authority center.

1. **Keep persistence singular.** ([Semantic Kernel](../docs/governance/product-design-contract.md#semantic-kernel)) Only `Attestation` persists.
   `Commitment` is transient intent compiled from official OpenSpec;
   Facts are observed anew and TransitionPlan is regenerated.
2. **Bind propositions.** ([Semantic Kernel](../docs/governance/product-design-contract.md#semantic-kernel)) An authorizing proposition names its subject,
   predicate, scope, plane, bindings, validity, verifier, and evidence.
3. **Fail closed.** ([Invalid-State Taxonomy](../docs/governance/product-design-contract.md#invalid-state-taxonomy)) Unknown required facts, ambiguous authority, stale bindings,
   contradiction, and model gap block effects and retirement.
4. **Project one way.** ([Projection Homomorphism](../docs/governance/product-design-contract.md#projection-homomorphism)) A projection may reduce presentation but cannot create
   authority, conceal an absence reason, or become its own source.
5. **Promote the model.** ([Model Promotion](../docs/governance/product-design-contract.md#model-promotion)) Preserve a lossless conflict, promote the smallest
   boundary, recompile, verify, then absorb or retire residue.
6. **Use Git at effect time.** ([Git-Native Repository Substrate](../docs/governance/product-design-contract.md#git-native-repository-substrate)) Recheck the exact Git binding and apply effects by
   compare-and-swap.
7. **Keep configuration singular.** ([Configuration Boundaries](../docs/governance/product-design-contract.md#configuration-boundaries)) A concern has one native owner; declarations
   and views link to it rather than repeat it.
8. **Keep profiles isomorphic.** ([Isomorphic Adopter Governance](../docs/governance/product-design-contract.md#isomorphic-adopter-governance)) Profiles select carriers and proof depth without
   changing the kernel or creating a second lifecycle.
