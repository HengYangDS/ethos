# Proposal

## Why

On 2026-11-04 two user-approved absorbed-ref retirements in governed adopters failed only at apply.
In both, `ethos lane retire absorbed-ref` previewed `ready_to_retire_absorbed_ref` and emitted its
apply command. The reference-transaction hook then refused the deletion in its prepared phase, so
`git update-ref` changed nothing.

- di-effect, `integration/dev`: the committed `[branch_roles]` table still declares it as the
  legacy candidate name, so the hook reported `legacy_role_ref_protected`. `candidate/dev` already
  held the same commit, and the closeout rename cannot create a ref that exists. No route could
  remove a legacy ref that carries nothing its successor lacks.
- alphasim, `work/ci-local-orphaned-board-test-20260714`: its accepted head has no release
  binding and an invalid profile, so no strict policy governs the deletion, and the hook reported
  `ref_move_policy_unavailable`.

The preview reads the work-tree branch-role policy and Git effect admission. It never evaluates the
two predicates that the prepared hook applies first.

## What Changes

- The absorbed-ref preview evaluates the prepared hook's legacy-role protection and ref-move policy
  resolution. They are the same predicates the hook uses, read without claiming the retirement's
  intent. A deletion that the hook would refuse now blocks the preview with the hook's own gap and
  no apply command.
- A legacy role ref whose standard successor ref already holds its exact commit is no longer
  protected from deletion alone. The absorbed-ref retirement may delete it, and the prepared hook
  admits that deletion without renaming any other legacy role. A legacy ref at another commit, or
  without a successor, stays protected as before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: an absorbed-ref retirement preview agrees with the prepared hook.
- `repository-paradigm`: deleting a legacy role ref whose successor holds its commit is admitted.

## Impact

`src/ethos/adapters/admission/role_rename.py`, `src/ethos/adapters/admission/ref_move_policy.py`,
`src/ethos/adapters/mutation/lane_retirement/absorbed.py` and a new focused test module. Adopters'
refs change only through their own approved retirements.
