## MODIFIED Requirements

### Requirement: Heavy local work is admitted host-wide

ETHOS SHALL admit heavy local work through one host-wide queue beside each repository's proof
slot. At most the declared slots SHALL run at once, in arrival order; a place SHALL last exactly
while its lock is held. A waiter SHALL keep its place behind live tickets up to its total or the
admission ceiling; its event and gap SHALL name the holder's operation, process and start
time. A holder record SHALL NOT contain command arguments, and a result SHALL NOT print a holder's
repository path.

#### Scenario: Two heavy runs share a host

- **GIVEN** a host that declares one slot
- **WHEN** two heavy runs ask for admission
- **THEN** the later waits until the earlier ends
- **AND** a third runs after both, in arrival order.

#### Scenario: A holder dies

- **WHEN** the process holding a place in the queue exits without releasing it and no other
  process inherited its lock
- **THEN** the next waiter is admitted without any cleanup by age.

#### Scenario: A holder dies while its work runs

- **GIVEN** a command that `ethos host run` admitted on a platform where a child inherits the
  place's lock
- **WHEN** the holder is killed while that command still runs
- **THEN** the place stays held until the last process that inherited the lock ends
- **AND** the next waiter is admitted then, without any cleanup by age.

#### Scenario: A holder leaves while a descendant keeps the lock open

- **WHEN** an admitted command returns and its holder leaves while a process that the command
  started still has the lock open
- **THEN** the place is free at once.

#### Scenario: A ticket's record cannot be removed

- **WHEN** a run gives up its place and the ticket's record cannot be removed
- **THEN** the ticket's lock is released all the same
- **AND** the next reader of the queue finds the place free.

#### Scenario: The wait reaches its bound

- **WHEN** a heavy run with a total of its own, such as `ethos host run --wait 12`, has waited
  that total behind a live holder
- **THEN** it ends without running, with `host_admission_contended:<operation>:<pid>:<since>` of
  the earliest live holder
- **AND** its next action is `ethos host status --json`
- **AND** the result holds no path of the holder's repository
- **AND** `--wait 0` asks once and does not wait.

#### Scenario: A live holder outlasts the repository's bound

- **GIVEN** a host of one slot and a repository whose `timeout.admission_seconds` is 3,600
- **WHEN** a run without a total of its own waits behind a holder that keeps the slot for 6,400
  seconds
- **THEN** it is admitted when that holder ends, in its place
- **AND** it records the 6,400 seconds it waited.

#### Scenario: The wait reaches the ceiling

- **WHEN** a run without a total of its own, or with one above the ceiling or one that is no
  number, waits behind a holder that never leaves
- **THEN** its wait ends at the declared maximum of `timeout.admission_seconds`, 36,000 seconds
- **AND** the gap names that holder.

#### Scenario: A waiter learns what it waits for

- **WHEN** a heavy run finds every slot held
- **THEN** it writes one `host_admission_waiting` event to stderr that names the holder's
  operation, executable, owner mark, process and start time.

#### Scenario: The holder runs an older engine

- **WHEN** the holder's record holds only a repository, an executable and a start time
- **THEN** the event shows an empty operation and owner mark, and the gap names the executable
- **AND** neither prints the repository.

### Requirement: Full proofs and nested work share the host admission

A full executing proof SHALL take its repository slot, then the host slot, then wait until two
consecutive 1-minute load samples fall within the limit; its bound SHALL NOT run behind a live
holder of the host slot. An executing host proof SHALL run its readiness gates without waiting and
SHALL hold the host slot, with no repository slot and no load wait, while its other gates run.
Work under a live admission SHALL join it, and a token SHALL admit nothing once its ticket's lock
is free.

#### Scenario: Work runs under a live admission

- **WHEN** a command that `ethos host run` admitted starts a proof or another admitted command
- **THEN** that work joins the live admission and does not wait for itself
- **AND** a copied token admits nothing once its ticket's lock is free.

#### Scenario: Work outlives its holder

- **GIVEN** a holder that was killed while the command it admitted still holds the place's lock
- **WHEN** that command starts another admitted command
- **THEN** the new command joins the place that its work still holds.

#### Scenario: Load dips once between busy phases

- **WHEN** one 1-minute load sample falls within the limit and the next does not
- **THEN** the proof keeps waiting until two consecutive samples fall within it.

#### Scenario: A host reports no load average

- **WHEN** admission runs on a host without a load average
- **THEN** the slot still serializes heavy runs
- **AND** the admission records the load as not measured.

#### Scenario: A full proof waits behind a long holder

- **GIVEN** a full proof whose admission bound is 3,600 seconds, behind a run that holds the host
  slot for 6,400 seconds
- **WHEN** that run ends and the load then falls within the limit
- **THEN** the proof is admitted in its place
- **AND** the time behind that run uses none of its bound.

#### Scenario: A full proof waits for its slot, then behind a holder

- **GIVEN** a full proof whose admission bound is 3,600 seconds, which waited 3,480 seconds for
  its repository's slot and then behind a run that holds the host slot
- **WHEN** that run ends and the load stays above the limit
- **THEN** the proof's wait ends with `proof_admission_contended` 120 seconds after that run ends
- **AND** only the time behind that run is left out of its bound.

#### Scenario: A full proof's whole wait reaches the ceiling

- **WHEN** the run ahead of a full proof never leaves
- **THEN** the proof's wait ends at the admission ceiling with `host_admission_contended` of that
  holder
- **AND** it runs no test or package gate.

#### Scenario: A full proof's place in the host queue cannot be written

- **WHEN** a full proof cannot open or read the host queue, cannot take its place in it, or
  cannot give it up after a normal end
- **THEN** it ends with `host_admission_unavailable`, and no OS error escapes
- **AND** a place that cannot be given up never replaces an exit already in flight, such as the
  contended gap or an interrupt
- **AND** its repository's slot is free for the next proof.

#### Scenario: A foreground host proof holds the host slot

- **WHEN** `ethos prove --host --execute --full` runs in the foreground
- **THEN** its readiness gates run without waiting
- **AND** it holds one ticket with the operation `proof.host` from its first test or package gate
  until its last gate ends
- **AND** its result records the seconds it waited.

#### Scenario: A host proof selects readiness gates alone

- **WHEN** an executing host proof's plan holds no test gate, no package gate and no gate that
  depends on one
- **THEN** it takes no ticket and does not wait.

#### Scenario: A host gate runs inside a full proof

- **WHEN** a gate of an admitted full proof runs an executing host proof
- **THEN** that host proof joins the live admission and takes no ticket.

#### Scenario: A host proof waits behind a long holder

- **WHEN** a holder keeps the host slot for longer than the repository's admission bound
- **THEN** the host proof is admitted when that holder ends, and runs its test and package gates.

#### Scenario: A host proof waits for the whole bound

- **WHEN** the host slot stays held by live tickets until the admission ceiling, the bound of a
  host proof's wait
- **THEN** the host proof runs no test or package gate
- **AND** it answers `block` with `host_admission_contended` and exits 1.

#### Scenario: The host root cannot be written

- **WHEN** an executing host proof cannot write its ticket under the host root
- **THEN** it answers `block` with `host_admission_unavailable` and exits 1.

### Requirement: One read lists the host queue and its holder

`ethos host status` SHALL be a catalog read that returns this host's declaration, its 1-minute load
and every live ticket in arrival order with its state, operation, executable, owner mark, process,
holder state and start time. The owner mark SHALL be the actor that the holder itself declared, or
empty. The read SHALL print no repository path, SHALL say only whether a ticket belongs to the
reading repository, and SHALL remove nothing from the queue.

#### Scenario: A holder and a waiter are listed

- **GIVEN** a host that declares one slot, one run that holds it and one that waits
- **WHEN** `ethos host status --json` runs
- **THEN** `data.queue` lists the first as `holding` and the second as `waiting`, in arrival order
- **AND** `data.declaration` carries the slots, the reserved CPUs, the load limit with its source,
  the CPUs and the worker cap.

#### Scenario: The holder belongs to another repository

- **WHEN** the reading repository is not the holder's
- **THEN** the holder's entry carries `same_repository` false and an empty owner mark
- **AND** the result holds no path of the holder's repository.

#### Scenario: The host is idle

- **WHEN** no live ticket exists
- **THEN** the read passes with an empty `data.queue`.

#### Scenario: A holder has exited

- **WHEN** a ticket's holder exited without leaving and no process holds its lock
- **THEN** the read does not list it
- **AND** the read removes no file; the next waiter removes the ticket.

#### Scenario: A holder is gone and its work runs

- **WHEN** a ticket's holder exited without leaving and the work that inherited its lock still runs
- **THEN** the read lists the ticket as `holding` with the holder state `gone`.

#### Scenario: The declaration is invalid

- **WHEN** `host.toml` is unreadable or out of range
- **THEN** the read answers `block` with the declaration's gap.
