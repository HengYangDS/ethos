# Design

## Decision

The existing `lane rebind-commitment` operation remains the sole mutation
owner. A read-only derive mode builds the existing `CommitmentRebindRequest`
from repository observations and persists a content-addressed receipt carrying
the request plus its digest. Apply may accept that receipt, load the request,
and run the existing admission and execution path unchanged. Thus the receipt
removes manual coordinate entry without becoming a second authority: current
Git, Lease, index, overlay, target commit, signature, and carrier observations
are all rechecked at apply time.

The derivation selects a target only when exactly one signed dangling commit is
compatible with the current HEAD, index tree, and carrier transition, or when
the caller names an exact target commit. Zero or multiple compatible targets
block with structured observations rather than guessing. Every blocker carries
`kind`, `observed`, `expected`, `retryable`, and one public `next_command` when
the next step is mechanically determined.

For archive closeout, an accepted `effect:openspec-archive` attestation already
binds the exact authorized paths. Those paths receive `authorized` attribution
from the effect itself; the old active Commitment glob is retained as context
but is not asked to authorize its own relocation into the archive namespace.
If effect verification fails, no archive authority is projected and existing
fail-closed behavior remains.

## Sequencing

1. Restore status/plan/prove/land congruence for authenticated archive effects.
2. Add derive receipt projection over the current rebind request contract.
3. Add receipt-bound apply and drift-negative tests.
4. Route hook and prewrite diagnostics through the same structured remediation
   projection.

## Deferred model work

Controller fencing, operation running receipts, the public transition graph,
readiness layers, traceability matrices, remediation schema generation, and
proof cache invalidation are accepted successor requirements. They are not
silently approximated here because each changes shared lifecycle contracts.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:Archive effect authorizes its exact transition paths` | `1.1` | `test_status_accepts_exact_authenticated_archive_effect` |
| `repository-governance:Invocation and editor bindings have distinct remediation` | `3.2` | `test_actor_and_editor_root_remediation_matrix` |
| `command-plane:Commitment rebind coordinates are publicly derived` | `2.1` | `test_rebind_derive_emits_receipt_for_exact_target` |
| `command-plane:Commitment rebind apply consumes an exact receipt` | `2.2` | `test_rebind_receipt_apply_and_drift_matrix` |
| `command-plane:Commitment rebind failures are directly actionable` | `3.1` | `test_commitment_rebind_required_projects_target_and_next_command` |
