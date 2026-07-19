## Why

The clean historical `work/github-hosted-ci-reconciliation-20260717` lane
contains 10 commits that remain patch-inequivalent to `dev`, even though a
semantic audit finds seven already absorbed behaviors, three obsolete records,
and no missing product behavior. Patch topology alone therefore cannot decide
whether the lane should land or remain forever visible.

A small accepted governance carrier is needed before any exceptional closeout.
It must preserve the exact historical state and fail closed until the native
resolution contract can enforce every required accepted, target, lease,
completion, recovery, and replay invariant.

## What Changes

- Bind the target branch and HEAD, audit-baseline accepted HEAD, clean state,
  active lease tuple, missing historical claim, and all 10 semantic
  dispositions.
- Record zero missing behavior and prohibit merge, rebase, cherry-pick, refresh,
  or land of the historical lane.
- Record that native v1 cannot bind accepted HEAD/relation or lease ID/epoch and
  cannot safely prove completion, replay, package/receipt integrity, or lease
  reconciliation for this target.
- Block `lane_resolution/preserve-retire` until a separate accepted product
  change implements those contracts, reconciles the contradictory completion
  record, and then supports a fresh post-acceptance audit and one-time decision.
- Record the duplicate-apply package rewrite as an operational follow-up only;
  no product-code fix, resolution authorization, or validity claim is included.
- Keep the carrier local-only and separate from remote or hosted evidence.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=github-hosted-ci-stale-lane-closeout;
  reuse=extend; change=modify; facet:lifecycle=observation,resolution,retirement;
  facet:surface=openspec,claim,evidence,docs;
  facet:authority=git,lease,claim,chronicle. A stale historical lane with a
  complete semantic matrix and zero missing behavior may be preserve-retired
  only after the native contract enforces every required binding and a fresh
  post-acceptance exact decision is prepared.

## Impact

- One active repository-governance Change, plan, claim, and dated Chronicle.
- No product source, historical lane, accepted/candidate root, remote, or hosted
  provider mutation.

## Out Of Scope

- Resolution apply, retirement, worktree cleanup, merge, rebase, cherry-pick,
  refresh, land, remote probe, push, or hosted-CI success claim.
- Product-code repair for decision binding, duplicate-apply idempotency,
  completion integrity, atomic preservation, or lease reconciliation.
