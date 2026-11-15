# Proposal

## Why

`host-reservation` gave a workstation one queue for heavy work, a reader of that queue and a
ticket that a foreground proof holds. This Change is the second half of the gate's row on the
host. Measured on the releasing host on 2026-11-14 and 2026-11-15:

- A proof that waits for its ticket at its test gates gives up after the admission timeout and
  requeues at the tail. Sessions wrap it in `ethos host run --wait` to keep its place.
- The worker cap is the CPUs less the reservation whatever the number of slots, so a second slot
  cannot open.
- One slot cannot tell a one-core hour from an eighteen-core minute: a one-core build held the
  slot for about 20 minutes while seven tickets waited.
- The rule of at most two tickets for one session is kept by each session's script. One session
  held four for two minutes, because several waiters passed the same check.
- Three of four live tickets declared no operation and no owner; only an engine of this release
  line writes them.
- `ethos host status --guest-cpus 20` on a host of 18 CPUs whose three guests hold 20 virtual CPUs
  reports `host_reservation_exceeded` with a next action that no value satisfies.
  `host-reservation` withdrew its task on this under DR-0016.
- An interrupted proof released its ticket while two of its gate process groups ran on, and its
  scratch of 5.9 GB stayed under the temporary root.
- One governed product's session found 5 of 16 problems only after a ticket had run on inputs they
  invalidate, and now admits heavy work on a receipt that binds each input by digest.

## What Changes

- A waiting proof keeps its place, or takes its ticket when it starts.
- The worker cap divides by the slots, and a ticket may declare the CPUs it uses.
- The queue keeps the cap of tickets for one holder and a rank among that holder's own waiting
  tickets.
- The guests' read counts what the guests may use at once, or its refusal names the guests' sizes
  as the repair.
- A ticket's release ends its work: the children of an interrupted holder end with it, and its
  scratch is removed or named.
- A work directory carries its owner's mark, which the direction design's build rules read.
- Candidate, not decided: a ticket is admitted on a readiness receipt that binds declared inputs
  by digest.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The host admission adapter, the host commands and the proof's host path, with their tests. The
test ceiling has 247 free lines, so the budget step lands first.

Owner: the release lead. Next action: converge the design and measure the patch. Read again: at
the cut of 0.2.0-beta.12.
