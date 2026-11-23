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
- No new key of the host declaration and no new refusal. One new file: the queue's entry gate,
  a lock file beside the queue directory (decision 3a).
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
   told which ticket is asking. The probe lets go before it answers. Two probes of one dead
   ticket can meet, and the second then counts it live until the next poll: a wait that is one
   poll longer, never an admission that should not be.
   3a. **Entries take turns, and each is named after every ticket present.** A place is counted
   only once its lock is held. An entry that has created its lock file and not yet locked it is
   therefore invisible, and without more two arrivals could each find the queue empty and both be
   admitted. So `enter` holds one lock for the whole of an entry, the queue's gate: a lock file
   beside the queue directory (`host-admission/v1.gate`), which no listing of tickets meets and
   no earlier release sees. Under it the entry reads the names present, names itself by the clock
   or by one more than the latest of them, creates its lock file, locks it, writes its record,
   and on POSIX only then renames the file from its `.pending` name to `.lock`. Two facts follow,
   and admission rests on them. The name order is the entry order, whatever the clock does. And
   when an entry ends, every ticket named before it has already taken its lock or is dead. A
   ticket therefore counts every live ticket ahead of it from its first reading on, and no later
   arrival is ever counted ahead of a ticket that was admitted.
   3b. **Only an entry waits for the gate.** A dead ticket's files are removed under the gate,
   where no entry is half-made, so a free lock there proves a dead ticket, also under a pending
   name. A read that finds the gate held removes nothing and answers from the locks; the next read
   removes it. `ethos host status`, a token's check and a waiter's poll never wait for the gate.
   An arrival waits for it one poll at a time inside its own wait, and holds no place meanwhile;
   an arrival whose wait ends there is answered `host_admission_unavailable`. A process killed
   inside the gate frees it, because the lock goes with its descriptor. A process stopped inside
   it delays arrivals, not the work that runs and not the readings of the queue. Windows cannot
   rename an open file, so there the file is named at once; the instant in which it is unlocked
   lies inside the gate, where only tickets named before it are counting. Only the process that
   entered a ticket leaves it: `leave` touches nothing of a ticket that was only read.
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
  entries take no gate and are named by the clock alone, so between two releases the instant in
  which two arrivals both find the queue empty stays as it is in that release, until every
  repository on the host runs this one.

## Proof Strategy

Unit tests drive the queue with real child processes: a holder killed with `SIGKILL` while its
child sleeps keeps the place until the child ends; a holder that leaves frees it while a child
still has the descriptor; the read lists the first as `holding` with its holder gone and creates
no file; a joined command joins a place whose holder is gone. An entry stopped between creating
its lock file and locking it, under each platform's naming, keeps a second process out until it
is whole; a clock set back names no arrival ahead of an admitted ticket; a held gate leaves an
arrival without a place and a read without removals. A journey with the built command repeats
the first two with `ethos host run` and records each reading of the queue.
