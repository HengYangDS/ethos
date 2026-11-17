# Design

## Context

See the [proposal](proposal.md). `host-reservation` left one queue under ETHOS's host root: a
ticket named by arrival time, pid and nonce, whose lock proves that its holder lives, and whose
name alone orders it. Three operations enter it. `ethos host run` and a host proof wait in
`admitted_host_work`, and a full proof waits in `admitted_full_proof`, which takes its repository's
slot first and waits for the load last. Both waits end at one bound counted from their start: the
caller's `--wait`, or `timeout.admission_seconds`, 3,600 seconds by default and at most 36,000 with
a recorded reason (`src/ethos/contracts/paradigm/paradigm.toml`).

Engines of several releases share the queue directory. Each engine applies its own rules to its
own wait, and the only things they share are a ticket's file name, its lock and the three fields
of its record. The first Change's design keeps those for the engines of earlier releases, and its
non-goals add no key to `host.toml`, which every released engine with the queue reads strictly.

The build tree has a work home, `build/runtime/work/<purpose>/`, which the artifact topology
allows and the configuration reference names. Nothing in a work directory says whose it is, and
nothing in the scratch that a proof's gates make under the temporary root does either. The
direction design's build rules give a work directory one owner and leave the way that owner is
read to this Change.

## Goals / Non-Goals

Goals:

- A proof, and any other heavy run, keeps its place behind tickets whose holders live, and every
  wait still ends.
- A second slot can open: the slots share the CPUs that the reservation leaves.
- The guests' read gives a repair that can be followed on a host whose guests hold as many virtual
  CPUs as it has, or more.
- A run's work directory and the scratch root of a proof's tests carry their owner's mark, and one
  function reads it.
- Every other measured case of the proposal has a decision with a size and a release.

Non-Goals:

- No new key in `host.toml`, no change to a ticket's file name or to the fields of its record,
  and no new environment variable.
- No new refusal for a command that a repository runs today. The three new gaps belong to the new
  `--work` option alone.
- No removal of a work directory or of scratch. The mark makes an owner readable; the reader and
  the previewed release are the direction design's.
- No hypervisor read, and no guest in the queue.

## Decisions

1. **A waiting run keeps its place behind live tickets.** A ticket ahead is live by its lock, and
   a holder that dies frees its place, so no bound runs while one is ahead: `ethos host run`
   without a total, a host proof and a full proof wait there until they are admitted.
   - **Rests on:** the proposal's first case, read from the queue's own records by the release
     lead on 2026-11-15 and not measured again by this patch: one holder kept the only slot for
     about 106 minutes with waiters present throughout, on a host whose declared bound is 3,600
     seconds. `HostQueue.live`, which lists only tickets whose locks are held and removes a dead
     holder's ticket. The wait's three consumers, read with
     `grep -rn "admitted_host_work(\|HostPlace(" src/ethos`: `run_admitted`, the host proof's
     `_admitted_gates` and `admitted_full_proof`. A regression drives each of the three behind a
     holder of 6,400 seconds.
   - **Considered:** (a) a bound that starts again when a holder ahead leaves, this patch's first
     form: it keeps a place while the queue moves and loses it behind one long holder, which is
     the measured case; (b) a longer `timeout.admission_seconds` in each repository: a tracked
     declaration in every repository for a property of one host, and any value below the longest
     hold still loses the place; (c) a heartbeat that each holder writes, so that a holder that
     hangs ends a wait before the ceiling: engines of earlier releases write none, so their live
     tickets would read as hung.
   - **Chosen because:** the lock already proves life and the queue already frees a dead holder's
     place, so a wait behind live tickets ends when they do, with no new record and no new order.
     The trade-off accepted: a holder that lives and hangs holds its waiters until their total or
     the ceiling, and the read names it.
   - **Applies to:** `host.run`, `proof.host`, and `proof.run` once it holds its repository's
     slot. A second full proof of one repository takes its ticket only after that slot, so it has
     no place to keep: it still ends at its bound while the first holds the slot. An engine of an
     earlier release in the same queue keeps its total bound.
2. **Every wait ends at the caller's own total, and at the admission ceiling at the latest.** The
   ceiling is the declared maximum of `timeout.admission_seconds`, 36,000 seconds, read by
   `ceiling_seconds`. `--wait` of `ethos host run` stays the caller's total, cut to the ceiling.
   - **Rests on:** the parameter's row in `src/ethos/contracts/paradigm/paradigm.toml`, default
     3,600 and bound 36,000; `RunRequest.wait`, the only total a caller gives. The regressions end
     a wait with no total, and one with a total of 40,000, at 36,000 seconds.
   - **Considered:** (a) no ceiling: a holder that hangs would hold a waiter without end; (b) a
     new parameter or a key of `host.toml` for the ceiling: one more declaration, and a key that
     earlier engines refuse; (c) `--wait` as a bound that a live holder suspends, like the
     repository's: a waiting run always has a live ticket ahead in this queue, so every value
     above zero would behave alike.
   - **Chosen because:** the declared maximum is already the longest wait a repository could
     declare, so no wait grows past what was admitted before. A caller that wrote `--wait` wrote a
     total, and it stays one.
   - **Applies to:** every admission wait of this engine. `--wait 0` asks once, and so does a
     total below zero, as before. A total that is no number ends at the ceiling: `--wait nan` and
     `--wait inf` waited without end on the commit before this Change, read there with a clock
     that the test advances and a holder that never leaves, so the request refuses neither. A
     proof has no total of its own: a caller that needs one keeps its own deadline, or runs the
     proof under `ethos host run --wait`.
3. **`timeout.admission_seconds` bounds a full proof's waits that no live holder of the host slot
   explains.** `AdmissionBound` leaves out of the bound the time between an answer behind a live
   ticket and the next question, and no other time. What the proof waited for its repository's
   slot stays used, so the wait for calm load that follows has what that wait left.
   - **Rests on:** the three waits of `admitted_full_proof`: for the repository's slot, for the
     host slot, and for two calm 1-minute samples 15 seconds apart. One regression waits 6,405
     seconds behind a render and then 30 for the load, under a bound of 3,600. A second, added
     after the review, waits 3,480 seconds for the slot and 15 behind a render, and ends its load
     wait at 3,615 seconds. Under this decision's first form, which moved the bound's start to
     the present behind a holder, the same wait ended at 7,080 seconds
     (`tests/unit/gates/test_proof_slot.py`).
   - **Considered:** (a) counting the load wait from the proof's start, as before: a proof that
     reached the slot after its bound would give it up at once, on a 1-minute load that still
     carries the run that just ended; (b) a whole bound for the load wait after any holder, the
     first form: the waits for the repository's slot and for calm load, which no live holder
     explains, could together last almost twice the bound.
   - **Chosen because:** the place a proof keeps includes the slot it has just taken, and the
     parameter stays one total for the waits it names. The trade-off accepted: a proof that used
     most of its bound for its repository's slot has only the rest for calm load, so the case of
     (a) returns for that proof alone.
   - **Applies to:** `proof.run`. Its wait for the repository's slot is bounded as before. A host
     proof and `ethos host run` have no repository slot and no load wait, so the parameter no
     longer bounds them, also where a repository declares a value below the default.
4. **A place that was given up is not resumed, and the ticket is not taken earlier.** A wait that
   ends leaves the queue, and its next attempt arrives at the tail.
   - **Rests on:** `HostQueue.admitted`, which admits a ticket when fewer than the declared slots
     of live names sort before its own, and is asked until it answers yes once and never again.
     New names sort last, so a ticket that was admitted stays admitted.
   - **Considered:** (a) a returned place that the same holder's next ticket takes up by its old
     arrival time. It inserts a name before waiters that may have just been admitted, so two runs
     can hold one slot; closing that needs a mark that every waiter writes before it starts and
     reads again after, which engines of earlier releases do not do. Estimated from the code, not
     measured: 120 product and 150 test lines. (b) Taking the ticket when the proof starts. It
     moves the arrival by the minutes of the readiness tier, holds the slot during that tier on an
     idle host, and makes a readiness-only plan take a ticket, against the accepted scenario.
   - **Chosen because:** decision 1 removes the measured loss without a new order in the queue.
   - **Applies to:** every operation. Resuming a place returns only with a queue whose every
     reader knows the mark, which is after 0.2.0.
5. **The worker cap is one slot's share.** `HostDeclaration.worker_cap` divides the CPUs that the
   reservation leaves by the declared slots, at least one.
   - **Rests on:** the proposal's second case, and the cap's two readers, read with
     `grep -rn "worker_cap(" src/ethos`: the environment of admitted work and the read's
     declaration.
   - **Considered:** leaving the cap whole, which costs the second slot: two runs would each start
     as many workers as the host has free CPUs.
   - **Chosen because:** the slots run at once, so they share. A host of one slot keeps its cap.
   - **Applies to:** work that this engine admits. An engine of an earlier release keeps the whole
     cap, so a host opens its second slot once every repository that queues on it selects an
     engine with the share.
6. **The guests' refusal names a repair that can be followed.** The reservation gains
   `reservable_cpus`, the host's CPUs less one, which is the most a declaration takes. A count at
   or below it is repaired by declaring that count; a count above it is repaired at the guests,
   and the next action names their sizes and the most they may hold in total.
   - **Rests on:** `read_host_declaration`, which refuses `reserved_cpus` at or above the CPUs,
     and task 5.4 of the archived `host-reservation`: three guests of 20 virtual CPUs on a host of
     18 that reserves 4. Not measured again here: this Change reads no hypervisor.
   - **Considered:** (a) counting what the guests may use at once in place of what they are
     configured with. Only the host's owner knows that number, ETHOS cannot check it, and any
     caller can pass one that fits. (b) A second gap code for the case that no value repairs,
     which costs a new code for the same refusal.
   - **Chosen because:** the guests' sizes are the owner's to decide, and the read's part is to
     say truthfully which of the two repairs exists.
   - **Applies to:** `ethos host status --guest-cpus`. The verdict, the gap code and the exit are
     unchanged; the next action's text and one member of `data.reservation` are new.
7. **A run names its work directory, and the directory carries the owner's mark.**
   `ethos host run --work <name>` creates `build/runtime/work/<name>/` in the repository and
   writes `.ethos-owner.json` in it before the run queues: the actor the run declared, its
   operation and the time. `work_owner` reads the mark.
   - **Rests on:** the direction design's build rules (`direction-carriers`, decision 9), which
     give a work directory one owner and call a directory whose owner cannot be read unknown and
     never residue; the accepted requirement that the owner mark is the actor a holder itself
     declared; the work home in `src/ethos/contracts/artifacts/topology.toml`.
   - **Considered:** (a) marking the directory a command happens to run in, which costs an effect
     that no caller asked for; (b) a registry under the Git common directory, which goes stale
     when a directory is moved or removed; (c) an owner in the directory's name, which breaks the
     rule that a work directory keeps its purpose's name.
   - **Chosen because:** a file inside the directory moves and ends with it, needs no queue to
     read, and an explicit option changes nothing for a run that does not name one.
   - **Applies to:** `host.run`. Decision 9 marks the scratch root of a proof's tests.
8. **A directory keeps its first mark, and an unknown owner is never taken over.** The mark is
   written whole beside its place and linked in, so of two owners that arrive together one holds
   the directory. Another owner's mark, or one that cannot be read, refuses the run with
   `host_work_owned:<name>`; a run that declares no actor writes no mark and enters no marked
   directory.
   - **Rests on:** the proposal's fourth case, where several waiters passed one check before any
     of them wrote; no measurement of its own.
   - **Considered:** the last writer's mark, which loses the first owner without a word; refusing
     a run that declares no actor, which costs a refusal where an unknown owner is already a
     state the build rules name.
   - **Chosen because:** a rule that every session must keep is kept once, at the door. The claim
     comes before the queue, so a refused run costs no place. The three codes fit the freeze on
     law: they can refuse only an invocation that uses the new option, and no invocation or tree
     that exists today is refused.
   - **Applies to:** file systems with hard links; elsewhere the claim answers
     `host_work_unavailable`. A mark is released by removing it or its directory, which stays a
     person's or the build reader's step. The record written beside the mark goes on every exit,
     also after a write that fails part way. One that cannot be removed lies in the directory
     that the mark governs and decides nothing: it refuses no claim, fails no scratch mark
     and replaces no exit in flight. Each refusal's repair can be followed in
     every case that raises it: a mark that names no owner is never taken over, and a file where
     the directory belongs is repaired at that directory. The repair of `host_work_owned` names
     `ETHOS_ACTOR` for the run's own identity, because `host run` alone takes no `--actor`: it
     hands that word to its child.
9. **The scratch root of a proof's tests carries the same record under a ticket.**
   `mark_ticket_scratch` writes it into the root that the Python behavior probe makes, when the
   probe's process holds or has joined a host ticket and declares an actor.
   - **Rests on:** the proposal's seventh case, and what the code shows: a proof's gates share no
     root. Six calls under `src/ethos/adapters/gates` each make a temporary directory directly
     under the default temporary root (`grep -n "TemporaryDirectory(\|mkdtemp("` over that
     package). One of them, the `mkdtemp` of `behavior_report`, makes the root that holds a test
     gate's synced environment, pytest's base directory, bytecode and coverage data, and it is the
     provider of this repository's own test gate (`system/repository-gates.toml`).
   - **Considered:** (a) one root for a run, by pointing the temporary root of admitted work at
     one marked directory: it changes the temporary path of every tool a gate starts, and a
     process keeps the temporary root it first resolved; (b) marking each of the six: the other
     five are each made and removed by a context of their own, and none was in the measured case;
     (c) naming the roots in the ticket's record: its fields are fixed for earlier engines, and
     the record goes when its holder dies, which is when the mark is needed.
   - **Chosen because:** one call makes the root whose loss was measured, and the record and its
     reader are decision 7's. A mark that cannot be written leaves the owner unknown and fails no
     attempt.
   - **Applies to:** the Python behavior probe in provider mode. Not covered: the other five
     directories, the JavaScript probe, and the scratch that a native command makes for itself,
     such as a repository's own test session. They get the mark where one call makes it: the
     row that gives a proof attempt one owned scratch, which the release-candidate plan names
     `proof-output-scratch`. Removing a root whose owner is gone is decision 11's.
10. **The cap of tickets for one holder, and a rank among them, follow 0.2.0.**
    - **Rests on:** the proposal's fourth and fifth cases: the cap needs an owner in every ticket,
      and three of four live tickets declared none.
    - **Considered:** building the cap now. It is a new refusal for a governed repository, which
      the freeze on law does not admit, and it would not bind tickets of earlier engines. A rank
      reorders waiters, which has the hazard of decision 4.
    - **Chosen because:** the cap is sound once counted after entry, among earlier names of the
      same owner, so no two waiters pass one check. Estimated, not measured: 35 product and 60
      test lines for the cap, 80 and 100 for the rank.
    - **Applies to:** the first batch after 0.2.0 that admits a refusal. Until then the read lists
      each ticket's owner to its own repository.
11. **A release that ends its work is built with the residue row, in a later batch.**
    - **Rests on:** the proposal's seventh case; `run_admitted`, which starts its command in the
      caller's process group; the two sites that start a group of their own, read with
      `grep -rn "process_group" src/ethos`.
    - **Considered:** ending the group in this Change. It touches the process adapter that every
      gate runs through, on three platforms, and removing scratch needs the proof of ownership
      that the accepted requirement on owned temporary resources asks for.
    - **Chosen because:** the size passes this Change's budget. Estimated, not measured: 90
      product and 120 test lines.
    - **Applies to:** 0.2.0-beta.13, beside the residue row. Decisions 7 and 9 give it the marks
      to read: a root that names an owner whose ticket no longer lives is proved owned.
12. **A declared CPU share is a later batch.** A ticket would declare the CPUs it uses, and
    admission would hold the sum of the shares ahead under the worker cap, in arrival order.
    - **Rests on:** the proposal's third case; no measurement of the share a light run needs.
    - **Considered:** building it now, which costs an admission rule that earlier engines do not
      read, and a request field; a class of light work that takes no ticket, which leaves its load
      uncounted.
    - **Chosen because:** counting in arrival order starves no waiter, and a ticket without a
      share counts as the whole cap, so an earlier engine stays safe. It needs its own measured
      acceptance. Estimated, not measured: 60 product and 90 test lines.
    - **Applies to:** 0.2.0-beta.13.
13. **A readiness receipt is not decided.**
    - **Rests on:** the proposal's last case, one session's reading of its own eight hours.
    - **Considered:** `host run` admitting a ticket only on a receipt that binds declared inputs
      by digest. A proof already runs its readiness tier before it takes the ticket.
    - **Chosen because:** one case from one repository does not fix a common form, and the
      fast-tier row owns the checks a receipt would name. Estimated, not measured: 60 product and
      90 test lines.
    - **Applies to:** after 0.2.0, with the fast tier.
14. **Tickets of earlier engines that declare no owner stay as they are.**
    - **Rests on:** the proposal's fifth case; the record's three old fields, which the first
      Change's design keeps.
    - **Considered:** refusing or hiding a ticket without an owner, which would stop the proofs
      of every repository on an earlier release.
    - **Chosen because:** each repository's bump to this release line ends the case.
    - **Applies to:** the read, which shows an empty operation and owner for such a ticket.
15. **A full proof gives its host place up through the place's own exit.** `admitted_full_proof`
    registers the release of its repository's slot first and `HostPlace.leave_on_exit` after it,
    so the place goes first and the slot goes whatever the place does. `HostPlace` answers
    `host_admission_unavailable` for an OS error of the queue at each of its reads: opening
    the queue, taking the place, naming the holder ahead and naming the contention.
    - **Rests on:** `HostPlace.leave_on_exit`, which `host-ticket-release` gave the waiting run,
      and the full proof's `finally`, which called `place.leave()` ahead of the slot's release
      with nothing around it, in 0.2.0-beta.10 as well
      (`git show v0.2.0-beta.10:src/ethos/adapters/gates/proof_slot.py`). Four regressions failed
      before the repair: an OS error while leaving escaped raw after a normal end, in place of
      the contended gap and in place of an interrupt, and an OS error while entering the queue
      escaped raw. After the normal end the repository's slot and its record were still held.
    - **Considered:** a guard of its own around `place.leave()` in the proof, which costs a
      second statement of what an exit in flight keeps; mapping the OS error of entering in the
      proof alone, which leaves the next caller of `HostPlace` to repeat it.
    - **Chosen because:** one owner already states the rule, and an exit stack runs the slot's
      release after it whatever it raises.
    - **Applies to:** `proof.run`, and through `HostPlace` every run that asks. `HostQueue.leave`
      releases a ticket's lock also when its record cannot be removed; the lock stayed held
      before, so that place stayed live until its process ended. The repository's slot goes
      also when its own record cannot be removed, and the next holder writes over that record.

## Risks / Trade-offs

- [A holder that lives and hangs holds its waiters] → Until their own total, or 36,000 seconds.
  The read names the holder, its process and its start time, and ending that process frees the
  place.
- [A proof's wait no longer ends at `timeout.admission_seconds`] → The changelog marks it
  breaking. A caller that needs a shorter total keeps its own deadline; a hosted job's time limit
  is one, and such a job then ends at that limit and not with the contended gap.
- [A second full proof of one repository] → It waits for the repository's slot outside the queue,
  ends at its bound as before, and queues at the tail once it has the slot. Giving it a place
  means taking the ticket before the slot, which the accepted requirement orders the other way.
- [Engines of earlier releases share the queue] → Order, names, locks and records are unchanged.
  An earlier engine ends its wait at its total bound and exports the whole cap.
- [The worker cap falls on a host that declares several slots] → That is the share that lets the
  slots run at once; a host of one slot is unchanged.
- [A mark outlives its owner] → A work directory then names an owner that no longer works in it,
  and refuses others until a person removes the mark. The build rules' reader reports it.
- [A file system without hard links] → A claim answers `host_work_unavailable` and the run does
  not start; a scratch root stays unmarked. A run without `--work` is unaffected.
- [The next action of `host_reservation_exceeded` changes its text] → The code, the verdict and
  the exit stay; a reader that matched the old sentence no longer matches.
