## Why

An adopter can keep a valid proof for one commit after upgrading ETHOS and
issue a new proof for the same commit under the current policy. Publication
still blocks: proof selection treats the old policy mismatch as corrupted
evidence before it considers the new current proof. Removing the old immutable
record is not a valid remedy.

## What Changes

- Distinguish an internally valid proof for a superseded policy from a broken
  proof envelope or artifact.
- Select only a proof matching the current canonical full/default policy for
  the exact source, intent and repository transition. An old-policy proof alone
  or explicitly selected old proof remains insufficient.
- Preserve global fail-closed behavior for tampered records, conflicting
  current proofs, stale source, wrong intent and missing current proof.
- Make accepted-ref hook admission use the same repository-transition proof
  predicate as promotion preflight; keep ordinary full-binding queries strict.
- Add owner-level positive and adversarial tests, then replay the observed
  adopter publication path with both immutable proofs still present.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: make current-policy proof selection coexist with
  immutable historical proofs without accepting them as current authority.

## Impact

The existing proof-attestation selection reducer, accepted-ref admission and
their tests. The accepted Attestation set, proof artifacts, policy compiler,
publication CAS and all recorded evidence remain unchanged; no revocation store
or cleanup command is introduced.
