## Context

An earlier Work Lane recorded the intended committed-profile behavior, but it
did not land to the current candidate baseline. Its archive is historical
context, not current product behavior. This Change must add the missing behavior
and pass its own proof floor without rewriting that history.

## Goals / Non-Goals

**Goals:**

- Add candidate-tree profile resolution, including the rule that a
  resolvable candidate tree without a profile is profile-absent.
- Compress implementation and regression code until the existing source-budget
  contract passes without new debt or allowance.
- Make the regression style-conformant and establish a reliable executed proof
  path before refreshing parity evidence.
- Keep evidence, archive history, candidate landing, accepted closeout, and
  remote publication as separate receipts.

**Non-Goals:**

- Changing default proof floors, gate descriptors, source-budget limits, or
  the independent-verifier boundary.
- Editing the archived Change, bypassing a failing gate, or treating a
  parallel-run crash as a passing proof.
- Landing, accepted-root closeout, or publishing this Change from this carrier.

## Decisions

### Preserve semantics while removing duplication

The implementation will use small, explicit seams in the profile reader and
test fixture. The focused regression exercises
an accepted-old profile, a different candidate profile, official closeout, and
raw-move refusal; it is not replaced by a mock of the hook.

### Pay for code with code, not policy debt

The active debt allowance is already exhausted for the current candidate
baseline.  The implementation and test fixture will be compressed or replaced
with smaller equivalent forms.  Raising baselines, adding a debt record, or
silently excluding paths would hide the cost rather than remediate it.

### Treat parallel instability as a testability defect

Focused tests first establish the intended behavior in a serial process.  The
full proof then uses the lowest reliable worker configuration that the product
command supports.  If the failure is product code, it is fixed; if it is host
parallelism, the exact executed proof records the reliable configuration rather
than calling a crashed run successful.

### Refresh parity only after the implementation commit is stable

Generic parity evidence is regenerated against the final implementation head,
committed with the Change, and followed by a new exact-HEAD proof.  It is not
copied, retargeted, or inferred from an earlier semantic revision.

## Risks / Trade-offs

- **A shorter regression can lose the hook boundary** -> retain both official
  closeout success and raw reference-move refusal assertions.
- **Tree reads can change missing-profile behavior** -> retain
  focused tests for resolvable-missing and synthetic-unresolved references.
- **Serial proof can hide a real concurrency defect** -> use it only after
  focused behavior passes; separately classify any remaining worker failure.
- **Parity refresh changes tracked evidence** -> regenerate only after a stable
  commit and bind later proof to that exact HEAD.

## Migration Plan

1. Complete this active carrier and admit every implementation path through its
   ETHOS scope companion.
2. Implement and test locally until formatting and source budget pass.
3. Commit the implementation, refresh generic parity evidence at that commit,
   then commit the evidence.
4. Run strict lifecycle validation and exact-HEAD executed proof.
5. Archive this Change only after its required tasks and proof are complete;
   candidate landing, accepted-root closeout, Work Lane retirement, and remote
   publication remain later transitions.
