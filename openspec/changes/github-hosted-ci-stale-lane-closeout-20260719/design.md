## Context

The target historical lane is clean and lease-bound at one exact HEAD, but its
10 patch-inequivalent commits do not represent 10 missing behaviors. Seven are
already absorbed and three are obsolete; the residual behavior count is zero.
The safe outcome is not integration or immediate retirement but a fail-closed
prerequisite record before a later preservation-first exceptional closeout.

## Goals / Non-Goals

**Goals:**

- Bind the exact target, accepted baseline, clean state, lease tuple, and
  ten-commit semantic matrix.
- Establish the accepted Chronicle and native-product prerequisites for one
  later exact `preserve-retire` decision.
- Preserve recoverability and block the effect while required bindings,
  completion integrity, replay, atomicity, or lease reconciliation are absent.

**Non-Goals:**

- No resolution effect, foreign authority, historical claim invention, product
  repair, remote action, or hosted-CI assertion.
- No integration of the historical lane by any Git topology-changing path.

## Decisions

1. **Semantic absorption is authoritative for integration intent.** Seven
   commits are absorbed, three are obsolete, and no behavior is missing; the
   lane must not be merged, rebased, cherry-picked, refreshed, or landed.
2. **Acceptance precedes product repair and exceptional resolution.** The active
   carrier records facts and prerequisites only. It authorizes neither a native
   decision nor apply.
3. **Current native v1 is insufficient.** Its decision cannot encode accepted
   HEAD/relation or lease ID/epoch; apply rechecks only the target observation,
   writes the final package before receipt collision handling, can retire before
   receipt completion, omits lease reconciliation, and inventory does not prove
   manifest/receipt integrity. A contradictory completion receipt already
   exists for the still-live target. The effect therefore fails closed.
4. **A separate product change owns the repair.** It must bind and revalidate
   accepted HEAD/relation plus lease ID/epoch, share strict completion-state
   verification across decide/apply/inventory/clear, install packages atomically,
   return `already_applied` without effects for a valid replay, reject conflicting
   state, validate receipts before destructive effects, reconcile the lease, and
   repair the contradictory live completion state.
5. **Preservation is verified before retirement.** The later package verifies
   the bundle, tracked patch, empty untracked inventory/archive, manifest
   digest, and immutable receipt. Recovery fetches or clones the bundle and
   applies the tracked patch.
6. **Duplicate apply remains a separate defect.** The July 19 package rewrite
   before receipt collision is recorded without fixing code or validating the
   mismatched package; a separate valid package protects the dirty all-lanes
   delta.
7. **Evidence planes remain separate.** Local carrier validation is not remote
   availability, push, hosted execution, or hosted-CI success.

## Risks / Trade-offs

- **Carrier acceptance is mistaken for apply authority** -> state explicitly
  that only the separately accepted product repair can unblock a later audit.
- **Patch inequivalence is mistaken for missing behavior** -> retain the full
  explicit semantic matrix and zero-residual conclusion.
- **Preservation package is ambiguous** -> require component verification,
  manifest digest, and an immutable receipt before any irreversible apply.
- **Operational incident is mistaken for repair evidence** -> keep the defect
  as a separate follow-up and reject the mismatched package.

## Migration Plan

1. Validate and commit this active carrier without applying resolution.
2. Accept a separate OpenSpec-governed product change implementing every native
   binding, completion, replay, atomicity, inventory, and lease requirement.
3. Reconcile the contradictory completion receipt and live target state without
   repeating an irreversible effect.
4. Record the current accepted HEAD, recompute target relation, reconfirm the
   complete disposition table and zero-residual result, and freshly observe all
   target and lease facts.
5. Prepare one native break-glass decision, create and verify the preservation
   package, and apply only with explicit irreversible confirmation.
6. Verify receipt, manifest, ref, worktree, and lease postconditions and retain
   the preservation package for recovery.
