# Proposal

## Why

The host queue exists so that at most the declared number of heavy runs share one workstation.
Its slot is an OS lock that only the holder process keeps: `ethos host run` starts the admitted
command without the lock. A holder that is killed, or that ends when its terminal closes, frees
the slot while the command it admitted keeps running, and the next ticket is admitted beside it.
Read in the code on 2026-11-22 and reproduced by a prototype the same day: after `SIGKILL` or
`SIGHUP` to the holder, a second run was admitted while the first command still ran.

On 2026-11-18 the host's swap filled and sessions and tickets were killed, which is the case that
triggers this. Whether two heavy runs then ran at once was not recorded.

The owner ordered the host queue layer first after 0.2.0-beta.11 (2026-11-20) and on 2026-11-23
chose to ship this repair ahead of the layer's records and readings.

## What Changes

- The admitted command inherits the ticket's lock. A place lasts exactly while its lock is held:
  by the holder, or, after a holder that exits without leaving, by the work that inherited it.
- A holder that leaves releases the lock for every process that inherited it, so a command that
  returns frees its place at once, as before, also when a process it started keeps running.
- `ethos host status` lists a held ticket whose holder is gone and says so (`holder`: `gone`).
- A token joins its admission while the ticket's lock is held, so work that outlived its holder
  does not wait behind its own place.

Windows, and the place a full proof takes for itself, keep the slot bound to the holder: no child
inherits a lock there.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: "Heavy local work is admitted host-wide" states how long a place lasts, changes the
  scenario of a holder that dies and gains two scenarios. "Full proofs and nested work share the
  host admission" binds a token to its ticket's lock, not to its holder, and gains one scenario.
  "One read lists the host queue and its holder" gains the holder state and one scenario, and its
  scenario of a holder that has exited is narrowed to a free lock.

## Impact

`ethos host run` on macOS and Linux; `ethos host status`; every caller that takes a place.

A place can outlast a killed holder for as long as a process that inherited the lock runs. A
process that never ends keeps the place until someone ends it; the read names such a ticket.
Nothing that passes today is refused. A caller whose holder is never killed sees no change.

A release without this change, sharing the queue directory, reads the same files and locks: it
keeps its own holder-bound slots and respects a lock that inherited work holds.

## Out Of Scope

- A record of each ended ticket, the memory readings, a caller's stated text and the read of
  ended tickets: the layer's second part.
- A run that outlives the desktop application that started it.
- A wait on memory readings before admission.
