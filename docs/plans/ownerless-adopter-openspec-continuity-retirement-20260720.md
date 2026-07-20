---
subject: ethos:ownerless-adopter-openspec-continuity-retirement-20260720
role: plan
state: active
relations:
  carrier: openspec/changes/archive/2026-07-20-ownerless-adopter-openspec-continuity-retirement-20260720
  source_lane: work/adopter-openspec-lifecycle-continuity-20260719
---

# Ownerless Adopter OpenSpec Continuity Retirement — 2026-07-20

Status: active, local-only authority carrier.

Purpose: record exact accepted absorption of one clean, lease-free, linked
adopter OpenSpec continuity lane and delimit one native exceptional retirement;
the resulting source branch and worktree must disappear rather than remain as a
permanent duplicate.

## Exact source boundary

The sole source is `work/adopter-openspec-lifecycle-continuity-20260719` at
`c5ad10361106b3062820a293cd1948c439f1ebf6`. At carrier admission its linked
worktree is clean, it has no active lease or bound active Claim, and its exact
head is a strict ancestor of accepted `dev` at
`0f3bdf3264a582082b99a212f7252bc2b051c374`.

The source's committed continuity packet and archived OpenSpec history are
already in accepted Git history. Its source-head delta is a historical generic
parity projection, so the accepted graph retains the useful committed semantics
without retaining this second worktree/ref. This is graph-backed absorption, not
a claim that historical runtime evidence, GitLab, GitHub, or hosted CI is
current.

## Required native transition

After this carrier is archived, proven at its exact HEAD, landed, and locally
closed out, it may create and apply exactly one `lane_resolution/retire`
decision for the named source. The resolver must re-observe the exact
branch/head, linked worktree, cleanliness, lease-free state, accepted Chronicle
bytes, and recovery plan before deleting that one branch/worktree; it must
require break-glass, irreversible confirmation, and write a receipt.

The source is clean, so no preservation package is needed. Its immutable Git
object remains recoverable through accepted history; any fact drift blocks
retirement rather than authorizing raw Git or lease deletion.

## Boundaries

This carrier does not cover predecessor
`work/adopter-openspec-lifecycle-20260714`, another lane, a valid lease,
remote mutation, hosted CI, publication, or a preservation package.

See also: [Adopter Boundary And Retirement](../governance/adopter-boundary-and-retirement.md),
[Runner and Mutation](../architecture/runner-and-mutation.md), and
[Repository Governance OpenSpec](../../openspec/specs/repository-governance/spec.md).
