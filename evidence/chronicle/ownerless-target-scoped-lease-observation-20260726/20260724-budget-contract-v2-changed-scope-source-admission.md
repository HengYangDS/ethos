---
subject: ethos:ownerless-target-scoped-lease-observation-20260726:budget-source-admission-predecessor
role: evidence
state: active
event: lane_resolution/retire
target_branch: work/20260724-20260724-budget-contract-v2-changed-scope-source-admission
target_head: 8afc80fd78a3d2c80144ae3d93d4045a004f3f54
claim: ownerless-budget-source-admission-predecessor-target-scoped-retry-20260726
---

# Target-scoped direct-retire probe for the RED predecessor

## Effect token

lane_resolution/retire

## Exact target

This Chronicle selects only
`work/20260724-20260724-budget-contract-v2-changed-scope-source-admission` at
`8afc80fd78a3d2c80144ae3d93d4045a004f3f54`. Accepted repair baseline
`b675cd64e79fa4e35000d8efd2b03465a0ab55fb` fixes only target-scoped lease
observation. It does not absorb the source commit or mint ownership over its
five valid-owner descendants.

## Immutable prior no-effect decisions

Decision `lane-decision:6e57ce11-5723-4171-85a8-596452f118fa` stopped at
Chronicle validation. Decision
`lane-decision:97d3e6ae-f0d4-41f0-a236-efa3896383c5` stopped at exact lease-state
unverifiability; its recorded worktree-registration observation later became
stale. Neither decision created a package, receipt, reservation, fence, ref, or
worktree effect, and neither may be reused.

## Bound successor

After this Chronicle and the target-scoped code repair are accepted, one fresh
direct-retire decision may select only the exact branch and HEAD above. It must
re-observe lease state, worktree registration, cleanliness, tree, accepted
HEAD, Chronicle bytes, and descendant containment without an intervening target
probe. Any drift leaves the source intact.

The only expected later boundary is
`lane_resolution_ownerless_target_not_accepted_ancestor`, which remains a
visible no-effect result. A separate accepted reconciliation is required before
any `preserve-retire` decision.
