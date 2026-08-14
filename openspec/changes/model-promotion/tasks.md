# Tasks

This is the only Model Promotion task ledger. Specifications own behavioral
coverage; tests and receipts prove it. Defect examples do not become tasks.

- [ ] **1. Promote the model.** Establish the single pure reducer, immutable
  transition receipt, operation-bound authority, and closed result contract;
  remove reusable Commitment permissions, Campaign, and parallel lifecycle
  state. **Proof:** contract/property tests and zero retired-owner residue.

- [ ] **2. Prove one complete transaction.** Move `refresh-base` onto
  `observe -> receipt -> exact-CAS apply -> post-observe -> Attestation`; terminal
  success requires converged ref, Lease, attachment, and fresh prewrite, while
  interruption yields exact compensation or one resumable partial receipt.
  **Proof:** mutation tests and a package-only vertical black box.

- [ ] **3. Complete the cutover.** Compile every remaining lifecycle, runtime,
  proof, and peer operation through the same reducer; derive command/help/schema
  projections from the same contracts; delete superseded orchestration and all
  compatibility paths. **Proof:** generated requirement-to-test matrix is
  complete and the full package-only topology matrix passes.

- [ ] **4. Accept the product.** Run read-only adopter compilation, fresh
  exact-HEAD full proof, OpenSpec archive, post-archive proof, signed governed
  land/closeout, immutable runtime activation, peer synchronization, and public
  housekeeping. **Proof:** one accepted source-independent runtime receipt binds
  source, tree, signature, wheel, entrypoint, schemas, proof, and runtime hashes.

## Requirement To Task To Proof

| Outcome | Requirement families | Evidence |
| --- | --- | --- |
| `kernel:*` | `1` | `tests:transaction-algebra` |
| `contracts:*` | `1` | `tests:operation-authority` |
| `adapters:*` | `2` | `tests:refresh-transaction` |
| `repository-governance:*` | `2` | `tests:lifecycle-reducer` |
| `command-plane:*` | `3` | `tests:command-projection` |
| `distribution:*` | `3` | `evidence:package-only` |
| `quality:*` | `3` | `evidence:positive-quality` |
| `proof-hosts:*` | `3` | `evidence:topology-matrix` |
