## Why

The preserved successor lane contains uncommitted refresh-base safety work, but
its source budget is blocked and its patch no longer applies cleanly to the
current `candidate/dev` baseline. Replaying that patch wholesale would risk
discarding newer current-contract behavior or advancing a Work Lane after its
admitted Git state has moved.

## What Changes

- Re-implement the still-missing SSH-signing preflight, snapshot revalidation,
  detached replay, and compare-and-swap safeguards for `lane refresh-base` on
  the current candidate-derived Work Lane.
- Add focused regressions that prove unavailable file-backed SSH signing,
  pre-rebase snapshot movement, and post-replay branch movement all fail closed
  without overwriting a newer Work Lane ref.
- Record a fresh, observation-bound resolution plan for the currently visible
  Work Lane cohort; preserved foreign lanes remain evidence sources until their
  own holder-bound or accepted exceptional decision is available.
- Keep source-budget enforcement intact: this replay must remove equivalent
  redundancy rather than raise a budget threshold or invent new debt.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=work-lane-refresh-base-safety; reuse=extend;
  change=modify; facet:lifecycle=preflight,replay,compare-and-swap;
  facet:surface=source,test,openspec,evidence,claim;
  facet:authority=git,lease,claim,executed-proof. Work Lane base refresh must
  bind SSH signing and Git snapshots before mutation, then atomically attach
  only the admitted branch generation.

## Impact

- `packages/ethos/src/ethos/adapters/mutation/lane_lifecycle/refresh.py`
- Focused Work Lane lifecycle and signing transport tests.
- This Change's claim, Chronicle, implementation plan, and local resolution
  inventory.

## Out Of Scope

- Mutating, retiring, deleting, or normalizing a foreign Work Lane merely from
  its visibility in the cohort.
- Raising source-budget limits, adding unrelated debt, remote push, hosted CI,
  registry publication, or release distribution.
