# Proposal

## Why

A proven Work Lane that changes holder cannot land. Its first holder proves the head under Lease
generation 1. The lane is then handed off natively, and the new holder proves the same head under
generation 2. The lane-level query marks the first proof stale, but a repository transition does
not apply the Lease check, so both proofs stay valid. Their assertions differ by verifier, so the
transition refuses `contradiction`, and no native verb removes the superseded proof. A governed
repository's beta.8 rebind was blocked this way on 2026-11-12.

## What Changes

- Among current proofs of one HEAD, a proof whose recorded Lease generation for a lane is lower than
  another valid proof's for the same lane is superseded: it drops out before the binding and
  contradiction comparisons.
- Proofs of one generation that differ in verifier or claim still contradict, as before.
- The Unreleased entry gains a Fixed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: a later Lease generation supersedes a lane's earlier proofs of the same
  HEAD.

## Impact

`src/ethos/adapters/mutation/proof_admission.py`, `tests/unit/kernel/test_proof_admission.py` and
`CHANGELOG.md`.
