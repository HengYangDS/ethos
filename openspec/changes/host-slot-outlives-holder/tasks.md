# Tasks

## 1. The place

- [x] 1.1 Pass the ticket's lock to the admitted command. Done when a holder killed with `SIGKILL`
      while its command runs keeps the place until that command ends, and a second run is admitted
      only then. (At `2f232aa08`, `test_a_killed_holder_leaves_its_place_to_the_work_it_admitted`
      passes: the waiter is refused while the admitted command runs and admitted once it ended,
      and no file is left.)
- [x] 1.2 Release the lock for every inheritor when the holder leaves. Done when a holder that
      leaves frees the place at once while a process its command started still has the lock open.
      (At `2f232aa08`, `test_a_holder_that_leaves_frees_its_place_for_every_inheritor` and
      `test_a_place_is_free_although_its_lock_file_cannot_be_removed` pass, each with a surviving
      process that inherited the descriptor.)
- [x] 1.3 Probe without creating. Done when a read of a queue whose lock file vanished creates no
      file and removes none. (At `2f232aa08`,
      `test_a_reader_that_races_a_leaving_holder_creates_nothing` passes: the read lists nothing
      and the directory stays empty.)
- [x] 1.4 Let entries take turns, each named after every ticket present. Done when an entry
      stopped between creating its lock file and locking it keeps a later arrival out under each
      platform's naming, and a clock set back names no arrival ahead of an admitted ticket. (At
      `2f232aa08`, `test_a_later_arrival_cannot_enter_while_an_entry_is_half_made` passes under
      the POSIX and the Windows naming with a second process, and
      `test_an_arrival_is_named_after_every_ticket_present_whatever_the_clock_says` passes.)
- [x] 1.5 Probe with a shared lock where the platform has one. Done when a reader inside its
      probe makes no dead ticket live for a token's check or for the next arrival. (At
      `2f232aa08`, `test_probes_of_one_dead_ticket_do_not_refuse_each_other` passes with the dead
      ticket's token in the environment: the run takes a place of its own.)
- [x] 1.6 Bound an entry and remove what it made. Done when a held gate or a held new lock leaves
      the arrival without a place and without files, an entry that fails at each stage leaves
      nothing, and a dead ticket's lock file is removed last. (At `2f232aa08`,
      `test_an_arrival_that_meets_a_held_gate_is_not_in_yet`,
      `test_an_entry_whose_own_lock_stays_held_gives_up_and_leaves_nothing`, the four stages of
      `test_an_entry_that_fails_leaves_nothing_and_no_place` and
      `test_a_dead_tickets_lock_file_goes_last` pass.)

## 2. The read and the token

- [x] 2.1 Name the holder's state. Done when the read lists a held ticket whose holder is gone as
      `holding` with `holder` `gone`, and no process is signalled where the platform is not POSIX.
      (At `2f232aa08`, the killed-holder test asserts `holding` with the holder's process number
      and `gone`, and `test_no_process_is_signalled_where_the_platform_is_not_posix` passes.)
- [x] 2.2 Join by the lock. Done when a command started by work that outlived its holder joins
      that place, and a token whose lock is free admits nothing. (At `2f232aa08`, the journey's
      join case with the built command, 21:52: after the holder is killed, the work's own nested
      `ethos host run` exits 0 as joined and a stranger's run is refused with
      `host_admission_contended`. `test_a_token_names_one_ticket_exactly` passes: a token whose
      lock was closed admits nothing, and no pattern is a token.)
- [x] 2.3 Ask a join again until the run is admitted. Done when a token that was live when the run
      was built and is free when it asks admits nothing and the run takes a place. (At
      `2f232aa08`, `test_a_run_joins_only_an_admission_that_is_live_when_it_is_admitted` passes.)
- [x] 2.4 Treat a run that is not in the queue yet as behind nobody. Done when a full proof's own
      bound ends a wait behind a held gate with no event, and the one event names the holder once
      the proof is behind one. (At `2f232aa08`, both cases of
      `test_a_full_proof_that_is_not_in_the_host_queue_yet_is_behind_nobody` and
      `test_a_run_that_was_not_in_yet_names_the_holder_it_then_waits_behind` pass.)

## 3. Evidence

- [x] 3.1 Run the journey with the built command. Done when `SIGKILL`, `SIGHUP` and a clean end
      with a surviving descendant are each recorded with the queue's readings. (At `2f232aa08`,
      2026-11-23 21:50, under a private data root. `SIGKILL`: the ticket reads `holding` with
      `holder` `gone`, a second run is refused, and it is admitted 11.5 s after the signal, when
      the 12-second command ended; no file is left. `SIGHUP`: the same, 11.6 s. Clean end: the
      queue is empty at once and a second run is admitted while the survivor still runs.)
- [x] 3.2 State the change in the changelog. Done when the Unreleased entry names the repair, the
      platforms it covers and the case of a process that never ends. (At `2f232aa08`, the entry
      under "Fixed" names the inherited lock, `holder` `gone`, entries that take turns, the shared
      probe on macOS and Linux, the process that never ends, and that Windows and a proof's own
      place stay bound to the holder.)
