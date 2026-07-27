# Axioms

This file is the machine-adjacent engineering reading of the
[root constraint](../docs/governance/product-design-contract.md#root-constraint).
It exists so tests, reviews, and contracts can refer to stable engineering
invariants without turning the root text into a subsystem, slogan, or tool ontology.

The canonical root text lives only in the Product Design Contract. This file
does not restate the verse and does not create a second truth center.

## Derived Axioms

1. **Authority before surface.** User instruction, repository truth, effective
   ChangeContracts, and Attestations outrank CLI names, hosted forges, assistant
   hosts, local state, generated views, and vendor surfaces.
2. **Signal before disorder.** Weak repository signals — drift, stale evidence,
   unbound propositions, HEAD mismatch, schema gaps, projection mismatch, dirty worktrees,
   and active carrier residue — are governance inputs, not background noise.
3. **Boundary before adapter.** Git remains Git; OpenSpec remains governance;
   CI remains a runner projection; agents remain collaborators; local state remains
   local. ETHOS governs admission, proof, promotion, and retirement boundaries.
4. **Passage before mechanism.** ETHOS governs the passage from question to
   repository law or bounded refusal. A governed commitment is the minimal
   auditable handle for that passage; practices, workflow runtimes, frameworks,
   skills, task graphs, and specs are vessels or carriers only when they clarify,
   test, or change that commitment.
5. **Evidence before proposition.** A proposition is bounded by the ChangeContract
   or Attestation that records it, the verifier that can establish it, and its
   authority, subject, scope, evidence digest, and HEAD binding. Metrics and reader
   projections explain readiness; they do not become authority.
6. **Parsimony before expansion.** An entity is justified only when it owns a
   distinct semantic obligation. Otherwise merge it, project it, archive it, or
   delete it.

## Use

Use these axioms in machine-adjacent checks, design audits, and code comments when
a stable engineering phrase is needed. Do not use philosophical labels or numbered philosophy references inside
low-level implementation, configuration, or provider projection files; state the
concrete engineering invariant instead.
