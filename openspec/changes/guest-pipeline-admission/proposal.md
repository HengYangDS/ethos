# Proposal

## Why

On a workstation that also runs CI guests, a hosted pipeline's jobs run in those guests beside
local heavy work, and the host queue knows nothing of them. The accepted model keeps the guests
inside the declared reservation (`reserved_cpus`), so that admitted work and guests share no CPU.
Measured on the releasing host between 2026-11-14 and 2026-11-16, by the release lane and by the
session that keeps that host's admission record:

- The model does not hold there. Three guests declare 20 virtual CPUs on 18 CPUs with a
  reservation of 4, and `ethos host status --guest-cpus 20` answers `host_reservation_exceeded`.
  By the keeper's reading, the guests' own processes used about 13 and about 8 cores during one
  pipeline each.
- A full proof waits for a calm 1-minute load also as the child of a ticket. Beside a pipeline
  that started outside the queue, one proof held the slot for 50 minutes and ran nothing.
- Two pipelines that started together failed one guest job and slowed another 3.5 times.
- The sessions of that host therefore keep a rule by their own scripts: a pipeline with guest jobs
  starts under one host ticket and holds it until its slowest guest job has ended. The one slot
  is then held for remote work. One install smoke of the release lane waited 3,084 seconds for
  its ticket, seven minutes of them behind such a hold.
- The read shows a holder's executable and its start, and nothing of what it holds the slot for.
  The release lead read such a holder as idle, because its only local process was a poll.

## What Changes

Candidates, none decided. The first is the accepted model's own repair and needs no code:

- The host's owner sizes the guests inside the reservation, or reserves what they hold; the
  guests' refusal names the value since `host-reservation-guests`. A pipeline then needs no
  ticket.
- A second named resource for guest pipelines, so that they exclude each other without holding
  the slot of local work.
- Proof admission that leaves the guests' declared share out of the load it waits for.
- A log of admissions and releases under the host root, so that "two at once" is read and not
  inferred.
- A ticket states what it holds the slot for, so that a hold for remote jobs does not read as
  idle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The host queue, its read and the guest guide. A named resource is an admission rule that engines
of earlier releases do not read, so it waits for a queue whose every reader knows it, as
`host-reservation-guests` decides for a rank and for a resumed place.

Owner: the release lead. Next action: say which candidate joins which batch, and tell the keeper
of the host's admission record before its review of 2026-11-21. Read again: at the cut of
0.2.0-beta.12.
