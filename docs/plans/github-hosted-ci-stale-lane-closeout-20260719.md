---
subject: ethos:github-hosted-ci-stale-lane-closeout-20260719
role: plan
state: active
relations:
  implements: github-hosted-ci-stale-lane-closeout-20260719
---

# GitHub Hosted CI Stale Work Lane Closeout — 2026-07-19

Status: active decision carrier; no lane-resolution effect has been performed.

Purpose: record the smallest accepted-governance foundation for a later,
one-time, exact `lane_resolution/preserve-retire` decision over one stale
historical Work Lane. This carrier does not mint authority over that lane and
makes no remote, push, or hosted-CI claim.

See the [active OpenSpec Change](../../openspec/changes/github-hosted-ci-stale-lane-closeout-20260719/).

## Bound Observation

| Fact | Bound value |
| --- | --- |
| Carrier branch | `work/github-hosted-ci-stale-lane-closeout-20260719` |
| Audit-baseline accepted/candidate HEAD | `4ddd805872ac5645617a5b290381cfd25c68464f` |
| Target branch | `work/github-hosted-ci-reconciliation-20260717` |
| Target HEAD and lease expected HEAD | `6d090e9c1fb0f0e6834d6f3818248923946800d4` |
| Target worktree state | clean, with empty tracked and untracked status |
| Target claim | missing; no historical claim is invented by this carrier |
| Lease holder | `agent:codex:thread:root` |
| Lease ID | `lease:11fc3869-8d38-4a86-94e5-2e2e6c68fab7` |
| Lease epoch | `1` |
| Patch-inequivalent commits | 10 |

## Ten-Commit Semantic Decision Matrix

| Commit | Classification | Intent and current decision |
| --- | --- | --- |
| `5febb9cf` | accepted/absorbed | Release mirror main implementation is already accepted. |
| `8bb25bb1` | accepted/absorbed | Release mirror core boundary is already accepted. |
| `4dcd3c26` | accepted/absorbed | Mirror closeout quality-ratchet repair is already accepted. |
| `9e285147` | accepted/absorbed | Node 24.18.0/26.5.0 compatibility, checksums, runner, and CI matrix are already accepted. |
| `6ab554ad` | accepted/absorbed | Land reader reuse of read-only workspace status is already accepted. |
| `e5674df1` | accepted/absorbed | Candidate dirty/proof-gate hygiene is already accepted. |
| `f5a1628c` | accepted/absorbed | Proof freshness test/import/ratchet cleanup is already accepted. |
| `1b8a6c44` | obsolete | Old parity receipt; it is not current proof or reusable authority. |
| `4ad38c17` | obsolete | Old parity receipt; it is not current proof or reusable authority. |
| `09d58b4c` | obsolete | Old lifecycle semantic-scope freshness, replaced by the exact-scope continuity successor. |

The residual product-behavior count is **0**. Therefore this historical lane
must never be merged, rebased, cherry-picked, refreshed, or landed.

## Post-Acceptance Decision Boundary

Only after this carrier and its Chronicle are accepted may a separately
admitted operator prepare one exact `lane_resolution/preserve-retire` decision.
The accepted HEAD above is the audit baseline, not a future immutable binding;
carrier acceptance advancing accepted truth does not self-invalidate this
record. The operator must record the then-current accepted HEAD, recompute the
target relation, and reconfirm all 10 dispositions and the zero-residual result
against that accepted truth before preparing the native decision.

The decision must bind that post-acceptance accepted HEAD and relation together
with the exact target HEAD, clean/dirty state, holder, lease ID, epoch, and lane
incarnation. Any target fact or accepted HEAD/relation change between decision
preparation and apply invalidates the decision and requires a new observation
and decision. An unavailable target also blocks the effect.

The later decision remains one-time and non-replayable. It must carry the
accepted Chronicle digest, exact evidence references, a break-glass assertion,
and the irreversible confirmation required by the native apply command. The
carrier itself runs neither decision apply nor retirement and does not transfer
or invent ownership.

## Preservation and Recovery Contract

Before the later irreversible effect, create and verify a content-addressed
preservation package containing the exact target bundle, a tracked patch, an
explicitly empty untracked inventory and absent-or-empty untracked archive, a
manifest digest, and an immutable receipt. Verify every component before
retirement. Recovery can fetch or clone the verified bundle to recreate the
branch and then apply the tracked patch; the manifest and receipt identify the
exact recoverable package.

## Operational Follow-up, Not Product Repair

On 2026-07-19 a duplicate resolution apply rewrote a preservation package
before immutable-receipt collision detection stopped completion. That
mismatched package is not declared valid here. A separate valid package protects
the dirty all-lanes delta. Product-code idempotency repair belongs to a separate
change and is not implemented or claimed by this carrier.

## Local-Only Closeout

Validation and commit of this carrier establish local repository truth only.
Remote probing, remote reconciliation, push, hosted execution, and hosted-CI
success remain unperformed and unclaimed.
