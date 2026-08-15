# Tasks

This is the only progress authority for this bounded model foundation. New
feedback is recorded as an Attestation and may be selected by a successor; it
does not append work here unless this Commitment already requires it.

- [x] **1. Freeze semantic identity.** Implement strict Commitment v2 and
  Attestation v2 value contracts, explicit identity-bearing fields,
  domain-separated digests, typed lineage/hypothesis/protocol values,
  composable canonical relations, opaque payload round-trip, and packaged golden
  vectors. **Proof:** source/wheel/package parity and property tests.

- [ ] **2. Establish the sole Attestation carrier.** Implement deterministic
  parentless Git set roots, hash-sharded canonical members, exact-CAS union,
  collision rejection, and minimal record/query projections. Remove current
  local and operation-specific Attestation authority; local bytes become staging
  or cache only. **Proof:** pure properties and real concurrent Git tests.

- [ ] **3. Close intent promotion.** Enforce non-authorizing selection,
  predecessor/selection binding, and one Commitment to one Change/lane/task
  authority. Remove current Claim, Chronicle, Ledger, Campaign, shared-inbox,
  reusable-permission, and duplicate-store selectors/producers while retaining
  historical bytes as inert history. **Proof:** architecture, import, residue,
  and negative authority tests.

- [ ] **4. Execute the destructive bootstrap.** Extend existing Commitment
  rebind with one `v1-to-v2-bootstrap` operation, opaque old lane/repository
  bindings, public staged-index target construction, one exact v2-generation
  plan, interruption recovery across branch/Lease/Attestation set, and terminal
  rejection of v1 current mutation. Rebind this lane and repository through
  public commands only. **Proof:** boundary mutation matrix plus package-only
  dry-run/apply/readback.

- [ ] **5. Accept the foundation.** Delete out-of-scope and superseded residue;
  run OpenSpec 1.8 strict validation, focused quality gates, code and ponytail
  review, exact-HEAD full proof, archive, post-archive proof, governed
  land/closeout, and accepted package-only readback. Record refresh and every
  other lifecycle family as selected successor Commitments, not tasks here.
  **Proof:** accepted exact-HEAD evidence and zero in-scope parallel authority.

## Requirement To Task To Proof

| Outcome | Task | Evidence |
| --- | ---: | --- |
| Commitment and Attestation v2 identity | 1 | `tests:semantic-v2-vectors` |
| Open payload and composable relations | 1 | `tests:semantic-v2-properties` |
| Deterministic Attestation set | 2 | `tests:attestation-set` |
| Bounded successor adoption | 3 | `tests:intent-promotion` |
| Exact one-shot v1-to-v2 cutover | 4 | `tests:commitment-v2-bootstrap` |
| Accepted bounded foundation | 5 | `evidence:model-promotion-closeout` |
