## Why

The clean historical `work/github-hosted-ci-reconciliation-20260717` lane
contains 10 commits that remain patch-inequivalent to `dev`, even though a
semantic audit finds seven already absorbed behaviors, three obsolete records,
and no missing product behavior. Patch topology alone therefore cannot decide
whether the lane should land or remain forever visible.

A small accepted governance carrier is needed before any exceptional closeout.
It must preserve the exact historical state and permit only a fresh,
post-acceptance, one-time native resolution.

## What Changes

- Bind the target branch and HEAD, accepted HEAD, clean state, active lease
  tuple, missing historical claim, and all 10 semantic dispositions.
- Record zero missing behavior and prohibit merge, rebase, cherry-pick, refresh,
  or land of the historical lane.
- Permit a later `lane_resolution/preserve-retire` decision only after carrier
  acceptance and a fresh exact observation, with break-glass, irreversible
  confirmation, preservation verification, and an immutable receipt.
- Record the duplicate-apply package rewrite as an operational follow-up only;
  no product-code fix or validity claim is included.
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
  only from a fresh post-acceptance exact decision.

## Impact

- One active repository-governance Change, plan, claim, and dated Chronicle.
- No product source, historical lane, accepted/candidate root, remote, or hosted
  provider mutation.

## Out Of Scope

- Resolution apply, retirement, worktree cleanup, merge, rebase, cherry-pick,
  refresh, land, remote probe, push, or hosted-CI success claim.
- Product-code repair for duplicate-apply idempotency.
