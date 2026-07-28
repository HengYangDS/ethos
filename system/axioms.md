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

1. **Persist only roots.** `Commitment` and `Attestation` persist semantic
   meaning; Facts are observed anew and TransitionPlan is regenerated.
2. **Bind propositions.** An authorizing proposition names its subject,
   predicate, scope, plane, bindings, validity, verifier, and evidence.
3. **Fail closed.** Unknown required facts, ambiguous authority, stale bindings,
   contradiction, and model gap block effects and retirement.
4. **Project one way.** A projection may reduce presentation but cannot create
   authority, conceal an absence reason, or become its own source.
5. **Promote the model.** Preserve a lossless conflict, promote the smallest
   boundary, recompile, verify, then absorb or retire residue.
6. **Use Git at effect time.** Recheck the exact Git binding and apply effects by
   compare-and-swap.
7. **Keep configuration singular.** A concern has one native owner; declarations
   and views link to it rather than repeat it.
8. **Keep profiles isomorphic.** Profiles select carriers and proof depth without
   changing the kernel or creating a second lifecycle.
