## Context

The target historical lane is clean and lease-bound at one exact HEAD, but its
10 patch-inequivalent commits do not represent 10 missing behaviors. Seven are
already absorbed and three are obsolete; the residual behavior count is zero.
The safe outcome is not integration but a later preservation-first exceptional
closeout after this decision becomes accepted truth.

## Goals / Non-Goals

**Goals:**

- Bind the exact target, accepted baseline, clean state, lease tuple, and
  ten-commit semantic matrix.
- Establish the accepted Chronicle prerequisite for one later exact
  `preserve-retire` decision.
- Preserve recoverability and invalidate the decision on target drift.

**Non-Goals:**

- No resolution effect, foreign authority, historical claim invention, product
  repair, remote action, or hosted-CI assertion.
- No integration of the historical lane by any Git topology-changing path.

## Decisions

1. **Semantic absorption is authoritative for integration intent.** Seven
   commits are absorbed, three are obsolete, and no behavior is missing; the
   lane must not be merged, rebased, cherry-picked, refreshed, or landed.
2. **Acceptance precedes exceptional resolution.** The active carrier only
   records a decision foundation. A later operator must use the accepted
   Chronicle and freshly recompute the exact target before deciding or applying
   `lane_resolution/preserve-retire`.
3. **Audit baseline and effect binding are distinct.** The carrier's accepted
   HEAD is the audit baseline. After acceptance, the decision preparer records
   the then-current accepted HEAD, recomputes target relation, and reconfirms
   the complete disposition table and zero-residual result. The native decision
   binds that accepted HEAD/relation together with target HEAD, dirty state,
   holder, lease ID, epoch, and lane incarnation. Any of those facts changing
   before apply blocks the effect and requires re-observation and a new
   decision.
4. **Preservation is verified before retirement.** The later package verifies
   the bundle, tracked patch, empty untracked inventory/archive, manifest
   digest, and immutable receipt. Recovery fetches or clones the bundle and
   applies the tracked patch.
5. **Duplicate apply remains a separate defect.** The July 19 package rewrite
   before receipt collision is recorded without fixing code or validating the
   mismatched package; a separate valid package protects the dirty all-lanes
   delta.
6. **Evidence planes remain separate.** Local carrier validation is not remote
   availability, push, hosted execution, or hosted-CI success.

## Risks / Trade-offs

- **Target changes after acceptance** -> invalidate the carrier authorization
  and re-observe before preparing a new decision.
- **Patch inequivalence is mistaken for missing behavior** -> retain the full
  explicit semantic matrix and zero-residual conclusion.
- **Preservation package is ambiguous** -> require component verification,
  manifest digest, and an immutable receipt before any irreversible apply.
- **Operational incident is mistaken for repair evidence** -> keep the defect
  as a separate follow-up and reject the mismatched package.

## Migration Plan

1. Validate and commit this active carrier without applying resolution.
2. After acceptance, record the current accepted HEAD, recompute target
   relation, reconfirm the complete disposition table and zero-residual result,
   and freshly observe the target HEAD, status, holder, lease ID, epoch, and
   incarnation.
3. Create and verify the preservation package and recovery materials.
4. Prepare one native break-glass decision and apply it only with explicit
   irreversible confirmation and an immutable receipt.
5. Re-observe the repository and retain the preservation package for recovery.
