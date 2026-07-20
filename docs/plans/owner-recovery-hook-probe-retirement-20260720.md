---
subject: ethos:owner-recovery-hook-probe-retirement-20260720
role: plan
state: active
relations:
  carrier: openspec/changes/archive/2026-07-20-owner-recovery-hook-probe-retirement-20260720
  target_lane: work/owner-recovery-hook-probe-20260720
---

# Owner-Recovery Hook Probe Retirement — 2026-07-20

Status: active local-only authority carrier.

Purpose: retain the provenance of one exact, clean, lease-free, unbound parity
probe in accepted history, replace its stale parity projection with current
accepted parity evidence, then retire the duplicate ref through the native
exceptional transition.

## Exact target and absorption

The sole target is `work/owner-recovery-hook-probe-20260720` at
`943a5e1e373b009f02533ff22815e8bca32b3157`. It has no linked worktree or
active lease and is an ancestor of accepted `dev`. Its only source-head delta
is an older `evidence/parity/generic-shadow.json` projection. Current accepted
history contains later executed parity projections and retains the source
commit as an ancestor, so the source's provenance is absorbed but its stale
projection is not reused as current evidence.

## Native transition boundary

After this carrier receives its own exact-HEAD proof, candidate land, and local
accepted closeout, `ethos lane retire unbound` may retire only this target with
the accepted Claim and Chronicle, exact head, reason, authorization,
break-glass, irreversible confirmation, and native compare-and-delete receipt.
Any drift preserves the ref.

## Non-claims

This does not authorize retirement of any sibling at the same historical head,
any leased or dirty lane, raw Git or SQLite deletion, remote mutation, hosted
CI, or publication.

See also: [Runner and Mutation](../architecture/runner-and-mutation.md),
[Command Plane](../reference/command-plane.md), and [Repository Governance
OpenSpec](../../openspec/specs/repository-governance/spec.md).
