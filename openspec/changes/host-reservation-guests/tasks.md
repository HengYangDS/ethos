# Tasks

## 1. The wait

- [ ] 1.1 `admitted_host_work` waits behind live tickets until its caller's total, and
      `run_host_command` and the host proof pass no bound of the repository's. Done when a run
      without `--wait` and a host proof are admitted behind a holder of 6,400 seconds, and
      `--wait 12` ends after 12.
- [ ] 1.2 `AdmissionBound` stops a full proof's bound while a live ticket holds the host slot
      ahead. Done when a full proof of bound 3,600 that took its repository's slot at once is
      admitted behind a render of 6,400 seconds and its load wait has the whole bound.
- [ ] 1.3 `ceiling_seconds` returns the declared maximum of a timeout or a caller's lower total,
      and both waits end there. Done when a wait with no total, one with a total of 40,000 and a
      full proof behind a render that never leaves all end at 36,000 seconds with the holder's
      gap.
- [ ] 1.4 `AdmissionBound` leaves out of a full proof's bound only the time behind a live holder
      of the host slot. Done when a proof of bound 3,600 that waited 3,480 seconds for its
      repository's slot and 15 behind a render ends its load wait at 3,615 seconds, and a proof
      with 9 seconds of its bound left keeps the length of its polls behind the render.
- [ ] 1.5 `admitted_full_proof` gives its place up through `HostPlace.leave_on_exit` ahead of its
      repository's slot, and `HostPlace.admitted` answers `host_admission_unavailable` for an OS
      error of the queue. Done when an OS error while leaving is that gap after a normal end and
      a note on the contended gap and on an interrupt, the repository's slot and its record are
      gone in each case, and a queue that cannot be written ends a full proof with that gap.
- [ ] 1.6 `ceiling_seconds` holds the declared maximum for a total that is no number. Done when a
      wait with a total of `nan` ends at 36,000 seconds, a full proof's bound of `nan` leaves
      the ceiling's remainder, and `--wait -1` asks once as before.
- [ ] 1.7 Every read of the host queue through `HostPlace` answers `host_admission_unavailable`
      for an OS error, a ticket's lock goes when its record cannot be removed, and the
      repository's slot goes when its own record cannot. Done when a full proof names the gap
      for an OS error while it opens the queue, names the holder ahead or names the contention,
      a ticket whose record stays is not live for the next reader, and a slot whose record
      stays is free for the next proof.

## 2. The worker cap

- [ ] 2.1 `HostDeclaration.worker_cap` divides the CPUs that the reservation leaves by the slots,
      at least one. Done when 8 CPUs give 3 workers for two slots that reserve 2, in the child's
      environment and in the read, and 2 for three slots.

## 3. The guests' read

- [ ] 3.1 The reservation carries `reservable_cpus`, and the next action names the value of
      `reserved_cpus` to declare, or the guests' sizes where no value holds them. Done when the
      read on 18 CPUs that reserve 4 passes for 4 guests' CPUs, names 12 for 12 and names 17
      virtual CPUs or fewer for 20.

## 4. The work directory

- [ ] 4.1 `claim_work_directory` creates one purpose's directory under the work home and links
      the owner's mark into it, and `work_owner` reads it. Done when a second owner, an unreadable
      mark and a run without an actor in a marked directory answer `host_work_owned`, a name that
      is not one lowercase directory answers `host_work_invalid`, and a tree that cannot be
      written answers `host_work_unavailable`.
- [ ] 4.2 `host run` takes `--work`, claims the directory before it queues, and reads each
      refusal's repair from the gap registry's three new rows. Done when the command finds its
      mark when it starts, a later run of the same owner keeps the mark, a refused run takes no
      ticket, and the argv table selects `host.run` for `host run --work render -- git status`.
- [ ] 4.3 `mark_ticket_scratch` writes the same record into the Python behavior probe's scratch
      root when its process holds or has joined a host ticket and declares an actor. Done when the
      root is marked while the tests run, carries no mark without a ticket or without an actor,
      and is removed with its mark.
- [ ] 4.4 `_mark` removes the record it writes beside the mark on every exit. Done when a write
      that fails part way leaves no file, a record that cannot be removed keeps an interrupt as
      the exit of a claim and of a scratch mark, and after a whole write and link the same
      record refuses the claim with `host_work_unavailable` and fails no scratch mark.
- [ ] 4.5 The repair of `host_work_owned` can be followed in every case that raises it. Done when
      another owner's mark, a mark that names no owner and a run without an actor each read a
      next action that names another directory, `ETHOS_ACTOR` for the run's own identity, which
      `host run` takes no flag for, and that a mark without an owner is never taken over.
- [ ] 4.6 The repair of `host_work_unavailable` can be followed in every case that raises it. Done
      when a file where the work directory belongs and a file where its tree belongs each read a
      next action that names the directory, what the run must be able to do in it and the run
      without `--work`, and a file system that links no file answers the same gap.

## 5. Documents

- [ ] 5.1 The reference's host section, the guide's sizing and work sections, the configuration
      reference's topology paragraph, the changelog and the spec delta. Done when Prettier, the
      documentation registry and `openspec validate host-reservation-guests --strict` pass.

## 6. Lane, hosted run and owner only

- [ ] 6.1 Run the precheck and readiness at the lane head, then the full proof. Done when each
      passes on the committed head.
- [ ] 6.2 Run the prose gate on the changed Markdown. Done when Vale and codespell pass.
- [ ] 6.3 Prove the place on the workstation: a bare proof behind one holder that outlasts the
      repository's admission bound is admitted after it. Done when its result records a wait
      longer than the bound and the read listed it as `waiting` throughout.
- [ ] 6.4 Prove mixed engines: an engine of an earlier release waits beside this one. Done when
      the earlier engine ends at its own total bound, this one keeps its place, and neither
      changes the other's order.
- [ ] 6.5 Run `ethos host status --guest-cpus <N>` on the reference host with the guests' own
      count. Done when the next action names a value that `host.toml` takes or the guests' sizes,
      and the owner has decided the sizes where it names them.
- [ ] 6.6 Run one render under `ethos host run --work <name>` on the workstation, and read the
      scratch root of one full proof's test gate while it runs. Done when both marks name the
      session's actor and a second session's run in the work directory is refused.
- [ ] 6.7 On the first hosted runs on both forges that carry this Change, observe a job that
      waits in the queue. Done when it keeps its place inside the job's own time limit and the
      worker count of the heavy test steps stays at its declared value.

## Workflow follow-up

- A run that joined an outer ticket does not state that ticket, and the outer run does not
  state its wait. Measured on 2026-11-15: a proof that waited about 65 minutes under
  `ethos host run` reported a wait of 0, so the weekly page's host minutes have no reader for
  the wait. Not built here. Read again at the cut of 0.2.0-beta.13, with the gate row that owns
  the proof's host path.
