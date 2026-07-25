---
subject: ethos:ownerless-closeout-admission-design-20260722
role: plan
state: archived
relations:
  derives_from: ownerless-first-batch-retirement-20260722
  superseded_by: native-lane-resolution-authority-design-20260724
---

# Ownerless Closeout Admission Design — 2026-07-22

Status: archived historical design, superseded by
[Native Lane Resolution Authority](native-lane-resolution-authority-design-20260724.md).
It is not an executable implementation or operational authority.

## Historical problem

A clean ownerless lane could have accepted semantic-absorption evidence while
remaining unable to use the then-current closeout route without inventing an
owner. Lane creation could also produce branch and sibling-worktree identities
that later closeout policy rejected. Raw Git deletion was correctly forbidden,
but no complete native transition existed.

## Durable decisions retained

The useful decisions survived the retirement of the original approach:

1. Never synthesize historical ownership; record the acting principal only as
   the executor of one exact effect.
2. Bind retirement to one immutable decision and Chronicle, exact branch, HEAD,
   registered path and incarnation, clean coordination, accepted ancestry, and
   current record integrity.
3. Keep the effect no-force and delete only the exact observed ref through
   compare-and-swap after accepted-ref verification.
4. Write a completion receipt only after explicit ref, registration, path,
   coordination, decision, and fence postconditions pass.
5. Create new Work Lanes with one canonical date-bound branch and matching
   sibling-worktree identity; route older layouts through explicit migration or
   resolution rather than silent reclassification.

## Superseded approach

The 2026-07-22 design attempted to obtain pre-effect admission from an
out-of-process provider-specific verifier. That split authority across products,
duplicated Git and worktree observation, introduced provider vocabulary into
ETHOS contracts, and left retry and recovery coupled to an unrelated runtime.
The approach, its wire shape, executable path, deployment steps, adapter, and
compatibility route are retired and are intentionally not reproduced here as
current guidance.

## Current authority

ETHOS now owns observation, admission, current records, fencing, reservation,
effect, retry, completed-effect recovery, cleanup, and receipts. The complete
current design and implementation sequence live in:

- [Native Lane Resolution Authority Design](native-lane-resolution-authority-design-20260724.md)
- [Native Lane Resolution Authority Implementation Plan](native-lane-resolution-authority-implementation-plan-20260724.md)
- [Command Plane](../reference/command-plane.md)

## Historical boundary

This archived document preserves why synthetic ownership, raw deletion, force,
and late unbound checks were rejected. It does not authorize an external
dependency, command invocation, adapter, schema, deployment, compatibility
surface, or Work Lane transition.
