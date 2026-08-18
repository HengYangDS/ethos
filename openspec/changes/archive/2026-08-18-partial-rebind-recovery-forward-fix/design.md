## Context

The rebind transaction owns one receipt, Git-effect plan, Attestation set, and
Lease CAS. Existing recovery expects a hook-projected Lease. The missing state
is earlier: the ref CAS persists, compensation fails, intent and evidence are
absent, and the Lease remains at the receipt's old generation.

## Design

1. Admit only the receipt target ref/tree/index/overlay and its old Lease or hook projection.
2. Recompile the original plan from the receipt and Lease.
3. Validate and reuse its sole Git-effect Attestation when present.
4. When intent and evidence are absent, recreate only the plan-bound intent and
   run the existing executor in recovery mode; it observes rather than mutates
   the target ref, persists evidence, and clears the intent.
5. Dry-run returns `ready_to_recover`; apply exact-CAS advances the Lease and
   emits the terminal rebind Attestation.

## Rejected Alternatives

- Reverse the ref: discards a successful effect.
- Edit SQLite: bypasses public authority.
- Add another command/store: duplicates the complete original receipt.

## Failure Semantics

Evidence/intent collisions and any Lease, receipt, ref, tree, index, overlay, or
authority drift fail closed. A target ref alone never grants recovery authority.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:Commitment rebind partial effects recover through the original receipt` | `1` | `test_partial_rebind_recovery_matrix`, drift/collision and checkpoint tests |
