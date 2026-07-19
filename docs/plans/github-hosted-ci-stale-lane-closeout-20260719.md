---
subject: ethos:github-hosted-ci-stale-lane-closeout-20260719
role: plan
state: active
relations:
  implements: github-hosted-ci-stale-lane-closeout-20260719
---

# GitHub Hosted CI Stale Work Lane Closeout — 2026-07-19

Status: active fact-and-prerequisite carrier; no lane-resolution effect is
authorized or has been performed.

Purpose: record the exact historical audit and the fail-closed prerequisites for
a later, separately governed `lane_resolution/preserve-retire` closeout. This
carrier does not authorize a native decision or apply, mint authority over the
target lane, or make a remote, push, or hosted-CI claim.

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

## Post-Acceptance Resolution Prerequisite

Acceptance of this carrier permits a fresh audit only; it does not authorize a
native decision or effect. The accepted HEAD above is the audit baseline, not a
future immutable binding, so carrier acceptance advancing accepted truth does
not self-invalidate this record.

The current native v1 decision records target HEAD, lane incarnation, holder,
path, dirty/foreign/orphan/ambiguous state, and tracked/untracked digests. It
does not encode accepted HEAD, relation to accepted truth, lease ID, or lease
epoch, and apply recomputes only the target observation digest. It therefore
cannot enforce the complete drift boundary required by the accepted
repository-governance contract. Current apply also lacks a strict reconciled
completion-state check, atomic package installation, pre-destructive receipt
collision handling, and lease reconciliation.

`lane_resolution/preserve-retire` remains blocked until a separate accepted
product change implements and tests those contracts, reconciles the existing
contradictory completion record for this target, and proves safe replay. Only
then may a separately admitted operator record the then-current accepted HEAD,
recompute the target relation, reconfirm all 10 dispositions and the
zero-residual result, and prepare one fresh, one-time decision that binds every
required accepted, target, and lease fact. Any drift or unavailable target
blocks the effect and requires a new observation and decision.

## Preservation and Recovery Contract

After the product prerequisite is accepted and before any irreversible effect,
create and verify a content-addressed
preservation package containing the exact target bundle, a tracked patch, an
explicitly empty untracked inventory and absent-or-empty untracked archive, a
manifest digest, and an immutable receipt. Verify every component before
retirement. Recovery can fetch or clone the verified bundle to recreate the
branch and then apply the tracked patch; the manifest and receipt identify the
exact recoverable package.

## Operational Follow-up, Not Product Repair

On 2026-07-19 a duplicate resolution apply rewrote a preservation package
before immutable-receipt collision detection stopped completion. Inventory can
still report that mismatched package as retained, and a historical completion
receipt for this target conflicts with its currently live ref, worktree, and
lease incarnation. Those records are not declared valid here. A separate valid
package protects the dirty all-lanes delta. Decision binding, strict completion
verification, atomic installation, safe replay, and lease reconciliation belong
to a separate product change and are not implemented or claimed by this
carrier.

## Local-Only Closeout

Validation and commit of this carrier establish local repository truth only.
Remote probing, remote reconciliation, push, hosted execution, and hosted-CI
success remain unperformed and unclaimed.
