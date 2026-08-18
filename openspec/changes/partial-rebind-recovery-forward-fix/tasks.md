# Tasks

- [x] **1. Define the partial-state authority.** Bind recovery to the immutable
  rebind receipt, exact old Lease generation, target ref/tree, index, overlay,
  holder, and plan; reject every coordinate drift before mutation.
- [x] **2. Prove both interrupted states.** Cover an existing plan-bound Git
  witness and the observed state where the target ref is durable while both the
  temporary intent and Git-effect Attestation are absent.
- [x] **3. Reconstruct only the original effect.** Recreate the sole receipt-
  bound intent, reuse the existing Git-effect executor in recovery mode, and
  advance the Lease through its existing exact CAS.
- [x] **4. Prove fail-closed recovery.** Cover plan collision, ref/tree/Lease/
  index/overlay drift, checkpoint recovery, and terminal Attestation emission.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| repository-governance:Commitment rebind partial effects recover through the original receipt | 1 | `tests:partial-rebind-exact-authority` |
| repository-governance:Commitment rebind partial effects recover through the original receipt | 2 | `tests:partial-rebind-interrupted-state-matrix` |
| repository-governance:Commitment rebind partial effects recover through the original receipt | 3 | `tests:partial-rebind-original-effect-reconstruction` |
| repository-governance:Commitment rebind partial effects recover through the original receipt | 4 | `tests:partial-rebind-fail-closed-recovery` |

After Task 4, use the governed commit, exact-HEAD proof, archive, post-archive
proof, land, accepted closeout, lane retirement, and package-runtime lifecycle.
Receipts and Attestations prove those post-task effects.
