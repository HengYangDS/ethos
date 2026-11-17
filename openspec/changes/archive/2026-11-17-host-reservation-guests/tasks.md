# Tasks

## 1. The wait

- [x] 1.1 `admitted_host_work` waits behind live tickets until its caller's total, and
      `run_host_command` and the host proof pass no bound of the repository's. Done when a run
      without `--wait` and a host proof are admitted behind a holder of 6,400 seconds, and
      `--wait 12` ends after 12.
- [x] 1.2 `AdmissionBound` stops a full proof's bound while a live ticket holds the host slot
      ahead. Done when a full proof of bound 3,600 that took its repository's slot at once is
      admitted behind a render of 6,400 seconds and its load wait has the whole bound.
- [x] 1.3 `ceiling_seconds` returns the declared maximum of a timeout or a caller's lower total,
      and both waits end there. Done when a wait with no total, one with a total of 40,000 and a
      full proof behind a render that never leaves all end at 36,000 seconds with the holder's
      gap.
- [x] 1.4 `AdmissionBound` leaves out of a full proof's bound only the time behind a live holder
      of the host slot. Done when a proof of bound 3,600 that waited 3,480 seconds for its
      repository's slot and 15 behind a render ends its load wait at 3,615 seconds, and a proof
      with 9 seconds of its bound left keeps the length of its polls behind the render.
- [x] 1.5 `admitted_full_proof` gives its place up through `HostPlace.leave_on_exit` ahead of its
      repository's slot, and `HostPlace.admitted` answers `host_admission_unavailable` for an OS
      error of the queue. Done when an OS error while leaving is that gap after a normal end and
      a note on the contended gap and on an interrupt, the repository's slot and its record are
      gone in each case, and a queue that cannot be written ends a full proof with that gap.
- [x] 1.6 `ceiling_seconds` holds the declared maximum for a total that is no number. Done when a
      wait with a total of `nan` ends at 36,000 seconds, a full proof's bound of `nan` leaves
      the ceiling's remainder, and `--wait -1` asks once as before.
- [x] 1.7 Every read of the host queue through `HostPlace` answers `host_admission_unavailable`
      for an OS error, a ticket's lock goes when its record cannot be removed, and the
      repository's slot goes when its own record cannot. Done when a full proof names the gap
      for an OS error while it opens the queue, names the holder ahead or names the contention,
      a ticket whose record stays is not live for the next reader, and a slot whose record
      stays is free for the next proof.

## 2. The worker cap

- [x] 2.1 `HostDeclaration.worker_cap` divides the CPUs that the reservation leaves by the slots,
      at least one. Done when 8 CPUs give 3 workers for two slots that reserve 2, in the child's
      environment and in the read, and 2 for three slots.

## 3. The guests' read

- [x] 3.1 The reservation carries `reservable_cpus`, and the next action names the value of
      `reserved_cpus` to declare, or the guests' sizes where no value holds them. Done when the
      read on 18 CPUs that reserve 4 passes for 4 guests' CPUs, names 12 for 12 and names 17
      virtual CPUs or fewer for 20.

## 4. The work directory

- [x] 4.1 `claim_work_directory` creates one purpose's directory under the work home and links
      the owner's mark into it, and `work_owner` reads it. Done when a second owner, an unreadable
      mark and a run without an actor in a marked directory answer `host_work_owned`, a name that
      is not one lowercase directory answers `host_work_invalid`, and a tree that cannot be
      written answers `host_work_unavailable`.
- [x] 4.2 `host run` takes `--work`, claims the directory before it queues, and reads each
      refusal's repair from the gap registry's three new rows. Done when the command finds its
      mark when it starts, a later run of the same owner keeps the mark, a refused run takes no
      ticket, and the argv table selects `host.run` for `host run --work render -- git status`.
- [x] 4.3 `mark_ticket_scratch` writes the same record into the Python behavior probe's scratch
      root when its process holds or has joined a host ticket and declares an actor. Done when the
      root is marked while the tests run, carries no mark without a ticket or without an actor,
      and is removed with its mark.
- [x] 4.4 `_mark` removes the record it writes beside the mark on every exit. Done when a write
      that fails part way leaves no file, a record that cannot be removed keeps an interrupt as
      the exit of a claim and of a scratch mark, and after a whole write and link the same
      record refuses no claim and fails no scratch mark.
- [x] 4.5 The repair of `host_work_owned` can be followed in every case that raises it. Done when
      another owner's mark, a mark that names no owner and a run without an actor each read a
      next action that names another directory, `ETHOS_ACTOR` for the run's own identity, which
      `host run` takes no flag for, and that a mark without an owner is never taken over.
- [x] 4.6 The repair of `host_work_unavailable` can be followed in every case that raises it. Done
      when a file where the work directory belongs and a file where its tree belongs each read a
      next action that names the directory, what the run must be able to do in it and the run
      without `--work`, and a file system that links no file answers the same gap.

## 5. Documents

- [x] 5.1 The reference's host section, the guide's sizing and work sections, the configuration
      reference's topology paragraph, the changelog and the spec delta. Done when Prettier, the
      documentation registry and `openspec validate host-reservation-guests --strict` pass.

## 6. Lane, hosted run and owner only

- [x] 6.1 Run the precheck and readiness at the lane head. Done when each passes on the committed
      head. Both passed at `4a5029e96` on 2026-11-17: the pre-check with 472 impacted test modules
      (9,555 passed, 5 skipped, no finding) and readiness with its 28 gates.
- [x] 6.2 Run the prose gate on the changed Markdown. Done when Vale and codespell pass.
- [x] 6.3 Prove the place on the workstation: a bare proof behind live holders that together outlast
      the repository's admission bound is admitted after them. Done when its result records a wait
      longer than the bound and the read listed it as `waiting` throughout. Observed on 2026-11-17
      with a host proof of the install smoke gate and no `host run` around it: it waited 4,316
      seconds under a bound of 3,600 and was admitted, and 35 reads of `ethos host status`, two
      minutes apart, each listed it as `waiting`. Seven tickets held the slot in turn; no one of
      them held it for the whole bound, which is the case that the regressions of decision 1 hold.
- [x] 6.4 Prove mixed engines: an engine of an earlier release waits beside this one. Done when the
      earlier engine ends at its own total bound, this one keeps its place, and neither changes the
      other's order. Observed on 2026-11-17: an engine of 0.2.0-beta.10 asked for the host with a
      total of 150 seconds while a ticket of this engine waited. The read listed it last, behind
      this engine's ticket, and it ended after 151 seconds with `host_admission_contended`. This
      engine's ticket kept its place, and the eight tickets stood in the same order before and
      after.
- [x] 6.5 Run `ethos host status --guest-cpus <N>` on the reference host with the guests' own count.
      Done when the next action names a value that `host.toml` takes or the guests' sizes.
- [x] 6.6 Run one render under `ethos host run --work <name>` on the workstation. Done when the mark
      names the session's actor and a second session's run in the work directory is refused with
      `host_work_owned:<name>`. Observed on 2026-11-17 on a scratch clone at the lane head, with a
      short command in place of a render: the mark named the session's actor and the operation
      `host.run` from the moment the run asked, and a run under another actor ended at once with
      `host_work_owned:<name>` and took no ticket.
- [x] 6.7 On the first hosted runs on both forges that carry this Change, read the heavy test job:
      its wait for admission, its end inside its own time limit and its worker count. Done when each
      reading is recorded for each forge, and a reading that the run's records do not hold is named.
      Read on 2026-11-17: on neither forge did a job wait, since each ran alone in its runner's
      queue and its proof records a wait of 0 seconds. GitHub's job ended in 38.7 of its 130 minutes
      with 4 test processes, the declared count, counted from the run's test results. GitLab's job
      ended in 20.8 of its 130 minutes; its declared count is 4, and neither its artifacts nor its
      proof's result record the count.

## Workflow follow-up

- A run that joined an outer ticket does not state that ticket, and the outer run does not
  state its wait. Measured on 2026-11-15: a proof that waited about 65 minutes under
  `ethos host run` reported a wait of 0, so the weekly page's host minutes have no reader for
  the wait. Not built here. Read again at the cut of 0.2.0-beta.13, with the gate row that owns
  the proof's host path.
- Owner: where the read on the reference host names the guests' sizes (20 virtual CPUs on 18 at the
  reading of 2026-11-15), decide the sizes; the read with the new count then passes or names a value
  to declare.
- Landing: the full proof runs on the archived head, where one proof serves every Change of the
  unit; its receipt is the landing's.
- Landing: while the full proof's test gate runs, read `.ethos-owner.json` in its scratch root under
  the temporary root, and record that it names the session's actor.
- A proof's result states no worker count, so a run's records cannot show that the cap held. Read
  again with the report of `gate-environment`, which states what a gate's child receives.
