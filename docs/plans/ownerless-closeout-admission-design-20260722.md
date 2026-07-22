---
subject: ethos:ownerless-closeout-admission-design-20260722
role: plan
state: active
relations:
  derives_from: ownerless-first-batch-retirement-20260722
---

# Ownerless Closeout Admission Design — 2026-07-22

Status: approved design; implementation has not started.

Purpose: define the fail-closed repair that permits semantically absorbed, clean ownerless lanes to retire without inventing ownership or bypassing repository-family checks.

## Problem

A clean ownerless lane may have an accepted Chronicle that proves semantic
absorption, yet its native retirement remains blocked because the repository
family closeout check requires an historical owner-task. Separately, native lane
start can create a branch that cannot satisfy the date-bound worktree-family
naming rule during later closeout. These failures leave clean, absorbed residue
without a legal transition while correctly blocking raw deletion.

## Decision

Introduce a narrow accepted-decision closeout mode and align lane creation with
the repository-family grammar.

1. The closeout admission accepts an explicit ownerless-resolution receipt,
   rather than inventing an owner task.
2. It validates the exact branch, HEAD, registered linked path, accepted
   Chronicle digest, decision/receipt identity, cleanliness, missing lease and
   claim binding, and accepted-ancestor relation immediately before effect.
3. The acting operator is recorded as executor only; it never becomes the
   historical lane owner and cannot satisfy valid-owner cases.
4. Lane creation emits `work/YYYYMMDD-slug` and a matching sibling-worktree
   directory. Legacy names require an explicit non-destructive migration route.

## Rejected approaches

- **Raw deletion after a manual inspection:** loses fail-closed admission and is
  forbidden.
- **Synthetic owner-task:** misstates ownership and could authorize valid-owner
  cleanup.
- **One-off exception records for each lane:** duplicates policy and leaves the
  same systemic defect.

## Transition flow

1. A current accepted carrier records one target-specific semantic decision.
2. `lane resolution decide` re-observes and writes its local decision record.
3. `lane resolution apply` creates the native receipt only when the same
   observation remains current.
4. Repository-family closeout consumes that receipt in ownerless mode, verifies
   all bindings, removes the linked worktree without force, and deletes only the
   exact observed ref.
5. A postcondition receipt records the executor, target, old head, Chronicle,
   decision and retirement result. Any mismatch preserves the lane.

## Error handling and boundaries

- Dirty, diverged, valid-lease, claim-bound, absent-path, stale-head, Chronicle
  drift, malformed legacy layout, or receipt mismatch all stop without deletion.
- Dirty ownerless lanes remain preservation-first and are out of this clean-lane
  transition.
- Valid-owner lanes remain holder-bound and out of scope.
- Existing malformed records and old worktree layouts are inventoried and
  migrated only through a separately admitted, recoverable path.

## Verification

Required regression coverage proves:

1. a clean ownerless accepted ancestor with a matching accepted decision can
   close;
2. a dirty or diverged target cannot use the clean ownerless path;
3. a valid lease or claim cannot use it;
4. a stale Chronicle, receipt, head, path, or postcondition blocks;
5. lane start emits grammar-compliant branch/path pairs; and
6. legacy naming is reported as migration-required rather than deleted.

## See Also

See also: [Ownerless First-Batch Retirement](ownerless-first-batch-retirement-20260722.md), [Authorized Work Lane Cohort Closeout](all-lanes-authorized-closeout-20260718.md), and [Detached Worktree Housekeeping](detached-worktree-housekeeping-20260719.md).
