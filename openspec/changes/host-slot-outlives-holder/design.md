# Design

## Context

`HostQueue.enter` locks `<ticket>.lock` through a `FileLock` object of the holder process and
`run_admitted` starts the command with `subprocess.run`. The lock is released when the holder
exits, whatever its child does. `admitted_host_work` leaves the place on every exit of the
`with` block, so the defect needs a holder that ends without running that exit: `SIGKILL`,
`SIGHUP`, or `SIGTERM` with no handler.

The lock is a BSD `flock` on POSIX. It belongs to the open file description, not to the process:
descriptors inherited across `fork` and `exec` share it, it is released when the last of them is
closed, and an explicit unlock through any of them releases it for all.

## Goals / Non-Goals

- A place lasts while the admitted work runs, also after its holder was killed.
- A clean end frees the place exactly as today.
- No new file, no new key of the host declaration, no new refusal.
- Not a goal: Windows, the place that a proof takes for itself, records of ended tickets.

## Decisions

1. **The work inherits the lock.** `enter` opens the lock file itself, takes the lock with
   `filelock.lock_descriptor` and returns the ticket with its descriptor. `run_admitted` passes
   that descriptor to the command (`pass_fds`). The place then lasts until the last process that
   holds the descriptor ends.
2. **Leaving unlocks for everyone.** `leave` removes the record, releases the lock with
   `filelock.unlock_descriptor` and closes the descriptor. The release frees the lock for every
   inheritor, so a command that returns frees its place at once although a process it started
   may still have the descriptor open. A prototype that only closed the descriptor left such a
   place held with no record, which the read could not list. Measured on macOS on 2026-11-23
   with the locked `filelock`: closing the holder's descriptor keeps the lock while a child has
   it; an explicit unlock by the holder frees it while that child still runs.
3. **A probe opens, never creates.** Readers test a ticket's lock through a fresh descriptor
   opened without creation; a lock file that is gone reads as free. A fresh descriptor in the
   holding process reads its own lock as held (measured the same day), so no reader needs to be
   told which ticket is asking. The probe answers and lets go at once, so no reader ever sees
   another reader's probe as a live holder.
   3a. **Naming and removal are exclusive.** A lock on `<queue directory>.reap` lies beside the
   queue's directory, so the queue holds tickets only. `enter` names, locks and records a ticket
   under it; `live` removes a free ticket under it and, when it cannot hold it, counts the ticket
   as live for that poll, which fails closed. Without that, a reader can remove the file of a
   ticket that an entrant has created and not yet locked, and the entrant then holds a lock on no
   file and is admitted beside another run. `record_ticket` checks that its locked file still has
   a name, as the second guard. On Windows an open file cannot be removed, so the reaper is never
   taken there. Only the process that entered a ticket leaves it: `leave` touches nothing of a
   ticket that was only read.
4. **The read names a holder that is gone.** A projected ticket carries `holder`: `present`,
   `gone`, or empty where the platform cannot tell. The probe is signal 0 on POSIX. On Windows
   `os.kill(pid, 0)` ends the process it names, so nothing is probed there.
5. **A token follows the lock.** `holds` already answers by live tickets; a ticket is now live
   while any process holds its lock, so work that outlived its holder still joins. Refusing a
   token whose holder is gone would need the pid probe, which a reused number defeats, and
   would make nested work wait behind its own place.
6. **Platforms.** `pass_fds` exists on POSIX only. On Windows, and for the place that a proof
   takes for itself (`proof.run` of a full proof and `proof.host` of a host proof: neither passes
   a descriptor to its gate children), the slot stays bound to the holder.

## Risks / Trade-offs

- [A process that inherited the lock from a killed holder never ends] -> The place stays held.
  `ethos host status` lists the ticket as `holding` with `holder`: `gone` and its process number;
  ending the process that still runs frees the place. No timer frees it: a place freed by age
  is the defect this change repairs.
- [A copied token admits for the life of the work, not of the holder] -> The same trust for a
  longer time, and only after a holder was killed.
- [An older release shares the directory] -> It probes the same lock files with the same
  primitive and removes a ticket only when its lock is free, so it respects inherited locks. Its
  reader releases its probe before it removes a free ticket's file, so the instant in which it
  can remove the file of a ticket that is entering stays as it is in that release.

## Proof Strategy

Unit tests drive the queue with real child processes: a holder killed with `SIGKILL` while its
child sleeps keeps the place until the child ends; a holder that leaves frees it while a child
still has the descriptor; the read lists the first as `holding` with its holder gone and creates
no file; a joined command joins a place whose holder is gone. A journey with the built command
repeats the first two with `ethos host run` and records each reading of the queue.
