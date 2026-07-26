## Context

The retired external-verifier worktree-closeout check is read-only. Its result
binds one lane
branch, head, path, decision, executor, accepted control head, missing
lease/Claim projection, clear path occupancy, and accepted-ancestor relation.
ETHOS owns the destructive effect and therefore must consume that admission at
the effect boundary rather than treating it as durable authority.

Three different coordination artifacts must not be conflated:

1. the SQLite target fence in the Git common directory, which competes with the
   lease writer;
2. the inventory-visible ownerless target reservation, which records the exact
   target, decision, phase, recovery state, and postcondition digest; and
3. the generic hidden receipt reservation, which prevents two writers from
   racing for one immutable completion-receipt path.

## Decision

Use a two-owner protocol:

1. The retired external verifier recomputes and returns exact read-only
   admission bindings.
2. ETHOS reads and strictly parses one decision-file snapshot. The canonical
   payload from those bytes must equal the already admitted decision object;
   all external-verifier, fence, reservation, and receipt fields derive from
   that single snapshot.
3. ETHOS validates the complete external-verifier response, then performs a
   SQLite
   BEGIN IMMEDIATE target-fence acquisition that atomically verifies no lease
   exists and reserves the lane/head for one decision and executor.
4. ETHOS re-reads decision bytes, accepted head, lane observation, lease/Claim
   projection, and path binding after the fence is held.
5. ETHOS prepares one Git reference transaction containing an accepted-ref
   verification and exact target-ref deletion, removes the clean worktree with
   no force flag, then commits the transaction.
6. A non-zero worktree-remove result is not assumed to mean zero effect. ETHOS
   re-observes the exact target ref, worktree registration, and path; only a
   fully unchanged target remains reserved_no_effect. A removed worktree with
   the ref still present becomes worktree_removed_ref_present; any other
   uncertain combination becomes transition_unknown.
7. ETHOS verifies target-ref absence with a three-state probe: present with an
   exact OID, explicitly absent, or unverifiable. Only explicit absence passes.
   It also verifies worktree registration absence, path absence, unchanged
   accepted head, missing lease/Claim, unchanged decision digest, and the
   expected fence before writing the completion receipt.
8. Receipt success releases the SQLite fence through exact CAS first. Only
   after that succeeds may ETHOS delete the visible ownerless reservation. If
   fence release fails, the visible reservation remains.
9. If a receipt is already durable after a crash or cleanup failure, retry
   validates the exact schema, decision, lane, head, and ownerless binding,
   re-reads one canonical decision snapshot, and re-verifies all effect
   postconditions. Explicit fence absence is accepted only when the exact
   immutable receipt authorizes cleanup; an unverifiable or different fence
   blocks. Recovery invokes neither the retired external verifier nor a Git
   effect and never rewrites the receipt.
10. Receipt-first cleanup remains convergent when reservation unlink completed
    before a crash. The exact receipt supplies only the cleanup binding; it does
    not recreate effect authority or permit a new destructive transition.

The retired external-verifier wire contract is the shape published by the
verifier main branch at `5137759`:
the coordination object contains exactly lease_state, claim_binding, claim_id,
and binding_digest. ETHOS validates every field and rejects unpublished
additions such as lease_id, holder_ref, or a nested lease object rather than
guessing future wire semantics.

Canonical and legacy artifact roots are read compatibility surfaces only.
When both roots contain an ownerless target reservation for one decision,
ETHOS compares the complete validated payload, including phase,
recovery_state, and postcondition_digest; any drift is a blocking conflict.

New completion receipts use schema_version = 2. The reader remains
one-way-compatible with historical unversioned receipts, while explicit
versions other than 2 are invalid and no legacy-shaped writer is retained.
Ownerless receipt executors are validated through the canonical HolderRef wire
contract. A damaged closeout-fence payload invalidates only the fence
projection; it does not rewrite an independently current lease schema as
invalid.

## Recovery states

- reserved_no_effect: the target and decision still match and ref,
  registration, and path are all unchanged; the same decision may recompute
  external-verifier admission and continue.
- effect_complete_receipt_missing: exact postconditions hold; before ordinary
  lane observation, the same decision may write the pre-bound receipt. If that
  receipt is already durable, retry validates it and performs cleanup only,
  whether the visible reservation remains or its unlink completed before a
  crash.
- worktree_removed_ref_present: the worktree effect occurred but the ref
  remains; no automatic continuation is allowed.
- postcondition_failed or transition_unknown: retain visible evidence and
  require explicit reconciliation.

A dangling symlink is still a present path and therefore fails closed. An
ordinary exception after the CAS boundary is classified as transition_unknown;
it is never silently downgraded to no effect.

## Module boundaries

- the retired external-verifier adapter: bounded read-only process and
  response contract, removed from current source.
- resolution/closeout/effect.py: ownerless target reservation, fence-aware
  effect orchestration, and postcondition validation over one canonical
  decision snapshot.
- resolution/closeout/cleanup/core.py: exact receipt-first recovery context and
  ordered fence, visible-reservation, and hidden-sidecar cleanup.
- resolution/closeout/recovery.py: public apply/recovery orchestration and
  partial-transition routing.
- resolution/records/core.py and resolution/records/inventory.py: durable record
  storage plus read-only artifact inventory and conflict projection.
- adapters/store/state/closeout.py: SQLite target-fence CAS and three-state
  inspection.
- receipts.py owns strict canonical decision parsing plus immutable receipt
  validation while retaining its pre-existing receipt and inventory entrypoints.
  `_effects.py` remains the concrete Git/worktree/external-verifier/state
  adapter and compatibility seam; lane.py keeps the pre-existing plan/apply entrypoints.
  This is a current dependency boundary, not a claim that newly added ownerless
  helpers were historical public APIs. Package __init__.py files remain
  declaration-only.

## Proof isolation

The armed-hook E2E creates temporary governed repositories. Those repositories
must not expose the caller's writable virtual-environment lib or include
directories. They expose only the real Python launcher plus a private
pyvenv.cfg and private site-packages directory that reads the caller's
dependencies. The test snapshots editable direct_url.json bindings before and
after the E2E and fails if the outer ETHOS runtime owner changes. This is a
proof-harness isolation contract, not a product-routing semantic.

## Security model

| Element | Binding |
| --- | --- |
| Asset | Exact worktree path and work/* ref at one HEAD |
| Actor | Explicit executor ref; never promoted to owner |
| External verifier | Retired source/host adapter at the deployed contract |
| Local exclusion | Git-common-directory SQLite target fence |
| Git effect | Accepted-ref verify plus exact target-ref delete CAS |
| Decision | One strictly parsed file snapshot used by every later binding |
| Evidence | Immutable receipt plus visible inflight/partial reservation |
| Receipt compatibility | v2 writes; read-only support for unversioned history |

The fence is local coordination, not distributed consensus. Safety comes from
atomic competition with the lease writer, full response validation, Git CAS,
post-effect verification, and visible crash recovery. Retired-verifier
unavailability, malformed output, field drift, active lease/Claim, dirty state, occupancy,
unverifiable ref or fence state, decision replacement, reservation drift,
postcondition drift, or receipt mismatch fails closed.

## Rejected alternatives

- Trusting ok=true or admission_mode alone: permits stale or forged binding.
- A decision-ID-only reservation: permits two decisions to compete for one
  lane/head.
- Holding one SQLite transaction across subprocess and Git operations: blocks
  unrelated state work and loses durable fence state on process failure.
- Treating any non-zero rev-parse as ref absence: converts inspection failure
  into false success.
- Treating a non-zero worktree-remove result as zero effect: hides partial
  filesystem or registration mutation.
- Rewriting an existing completion receipt during recovery: violates immutable
  evidence and cannot distinguish an exact receipt from a conflicting one.
- git worktree remove --force: violates the clean-ownerless contract.
- Editing or rebasing the foreign predecessor lane: violates holder authority
  and would import code based on an obsolete accepted base.
