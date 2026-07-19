---
subject: ethos:ownerless-unbound-ancestor-retirement-20260719
role: plan
state: active
relations:
  implements: ownerless-unbound-ancestor-retirement-20260719
  extends: worktree-retirement-exceptional-unbound-v2-20260719
---

# Ownerless Unbound Accepted-Ancestor Retirement — 2026-07-19

Status: active, local-only retirement-evidence carrier.

Purpose: record exact accepted absorption and target-specific authority for one
currently lease-free unbound `work/*` ref that is a strict ancestor of the
accepted branch. This carrier never converts the wider inventory into deletion
authority.

## Exact Targets

| Ref | Head | Current relationship |
| --- | --- | --- |
| `work/20260719-worktree-retirement-fail-closed` | `1fca210fd3550bcd62d127a3f9910ed1ff80523c` | accepted ancestor, unbound, no active lease |

## Boundary

The carrier proves only that the accepted repository contains the relevant
behavior and durable evidence, and that the listed residue has its own active
Claim and accepted Chronicle. It does not claim that a historical tree is
byte-identical to the accepted tree, take over a foreign lease, delete a
diverged or dirty lane, mutate GitHub or GitLab, or claim hosted CI.

After this carrier is proven, landed, and locally closed out, the target must
be dry-run again with its own exact head, reason, Chronicle, break-glass, and
irreversible confirmation. A changed ref, linked worktree, active lease, Claim
drift, Chronicle drift, or protected-ref drift blocks the target.

The inventory additionally observed active leases on
`work/openspec-archive-logical-identifier-20260719` and
`work/quality-zero-exceptions-successor-v2-20260719`; they are explicitly out
of scope and remain protected pending their lease holders' own lifecycle.

See also: [All Work Lanes Convergence Implementation Plan](all-work-lanes-convergence-implementation-plan-20260716.md), [Runner and Mutation](../architecture/runner-and-mutation.md), and [Repository Governance OpenSpec](../../openspec/specs/repository-governance/spec.md).
