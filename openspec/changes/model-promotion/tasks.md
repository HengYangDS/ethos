# Tasks

This is the only progress authority for this bounded model foundation. New
feedback is recorded as an Attestation and may be selected by a successor; it
does not append work here unless this Commitment already requires it.

- [x] **1. Freeze semantic identity.** Implement strict Commitment v2 and
  Attestation v2 value contracts, explicit identity-bearing fields,
  domain-separated digests, typed lineage/hypothesis/protocol values,
  composable canonical relations, opaque payload round-trip, and packaged golden
  vectors. **Proof:** source/wheel/package parity and property tests.

- [x] **2. Establish the sole Attestation carrier.** Implement deterministic
  parentless Git set roots, hash-sharded canonical members, exact-CAS union,
  collision rejection, and minimal record/query projections. Remove current
  local and operation-specific Attestation authority; local bytes become staging
  or cache only. **Proof:** pure properties and real concurrent Git tests.

- [x] **3. Close intent promotion.** Enforce non-authorizing selection,
  predecessor/selection binding, and one Commitment to one Change/lane/task
  authority. Remove current Claim, Chronicle, Ledger, Campaign, shared-inbox,
  reusable-permission, and duplicate-store selectors/producers while retaining
  historical bytes as inert history. **Proof:** architecture, import, residue,
  and negative authority tests.

- [x] **4. Execute the destructive bootstrap.** Extend existing Commitment
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
| `contracts:Commitment v2 identity is explicit and bounded` | `1` | `tests:semantic-v2-vectors` |
| `contracts:Attestation v2 payload and relations are open and composable` | `1` | `tests:semantic-v2-properties` |
| `contracts:Selection Attestations never mint authority` | `3` | `tests:intent-promotion` |
| `adapters:Attestations use one deterministic Git set carrier` | `2` | `tests:attestation-set` |
| `adapters:Non-authoritative Attestation stores are not current readers` | `2` | `tests:attestation-set-authority` |
| `command-plane:Attestation record and query project one set contract` | `2` | `tests:attestation-command-plane` |
| `command-plane:Commitment rebind owns one destructive v2 bootstrap` | `4` | `tests:commitment-v2-bootstrap` |
| `repository-governance:Continuous intent preserves bounded Changes` | `3` | `tests:intent-promotion` |
| `repository-governance:One Commitment binds one Change and lane generation` | `3` | `tests:generation-binding` |
| `adapters:*` | `2` | `tests:adapter-model-promotion` |
| `command-plane:*` | `4` | `tests:command-plane-model-promotion` |
| `contracts:*` | `1` | `tests:semantic-v2` |
| `kernel:*` | `3` | `tests:semantic-kernel-reduction` |
| `repository-governance:*` | `3` | `tests:repository-governance-reduction` |
