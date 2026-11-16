## MODIFIED Requirements

### Requirement: Heavy local work is admitted host-wide

ETHOS SHALL admit heavy local work through one host-wide queue beside each repository's proof
slot. At most the declared slots SHALL run at once, in arrival order; a holder's exit SHALL free
its place without cleanup. A waiter SHALL keep its place behind live tickets up to its total or
the admission ceiling; its event and gap SHALL name the holder's operation, process and start
time. A holder record SHALL NOT contain command arguments, and a result SHALL NOT print a holder's
repository path.

#### Scenario: Two heavy runs share a host

- **GIVEN** a host that declares one slot
- **WHEN** two heavy runs ask for admission
- **THEN** the later waits until the earlier ends
- **AND** a third runs after both, in arrival order.

#### Scenario: A holder dies

- **WHEN** the process holding a place in the queue exits without releasing it
- **THEN** the next waiter is admitted without any cleanup by age.

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

### Requirement: The host declaration bounds admitted work

The host declaration SHALL be the only host-wide authority for the slot count, the reserved CPUs
and the load limit. A value out of range SHALL be refused with a named gap and not clamped, and
admitted work SHALL receive a worker cap of one slot's share of the CPUs that the declaration
leaves, at least one. The cap SHALL keep a smaller positive worker count that the caller's
environment already declares.

#### Scenario: The host declaration is out of range

- **WHEN** `host.toml` declares zero slots, reserves every CPU or declares a load limit that is not
  positive
- **THEN** admission refuses with a named gap and does not clamp the value.

#### Scenario: Busy guests hold the host's load

- **GIVEN** CI virtual machines that keep the host's load above half its CPUs
- **WHEN** `host.toml` declares a higher `load_limit`
- **THEN** a full proof admits under that limit, and a wait that reaches its bound names the load,
  the limit and where the limit came from.

#### Scenario: A caller declares fewer workers

- **GIVEN** an environment that sets `PYTEST_XDIST_AUTO_NUM_WORKERS` to 4 on a host of one slot
  whose declaration leaves 8 CPUs
- **WHEN** work is admitted
- **THEN** its children receive 4 workers
- **AND** `ETHOS_HOST_CPU_CAP` carries 8.

#### Scenario: Two slots share the CPUs

- **GIVEN** a host of 8 CPUs that declares two slots and reserves 2 CPUs
- **WHEN** work is admitted
- **THEN** `ETHOS_HOST_CPU_CAP` carries 3
- **AND** the read reports the same worker cap.

### Requirement: Full proofs and nested work share the host admission

A full executing proof SHALL take its repository slot, then the host slot, then wait until two
consecutive 1-minute load samples fall within the limit; its bound SHALL NOT run behind a live
holder of the host slot. An executing host proof SHALL run its readiness gates without waiting and
SHALL hold the host slot, with no repository slot and no load wait, while its other gates run.
Work under a live admission SHALL join it, and a token whose holder has exited SHALL admit
nothing.

#### Scenario: Work runs under a live admission

- **WHEN** a command that `ethos host run` admitted starts a proof or another admitted command
- **THEN** that work joins the live admission and does not wait for itself
- **AND** a copied token whose holder has exited admits nothing.

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

### Requirement: The guests' CPUs are checked against the reservation

Given the guests' virtual CPU count, `ethos host status` SHALL report whether it fits inside the
declared `reserved_cpus` and the most this host can reserve, and SHALL answer `block` with
`host_reservation_exceeded` when it does not fit. Its next action SHALL name the value to declare,
or the guests' sizes where no value holds them. The count SHALL come from the request, whose
caller reads it from the guests' own configuration; ETHOS SHALL read no hypervisor.

#### Scenario: The guests fit

- **WHEN** `ethos host status --guest-cpus 4` runs on a host of 18 CPUs that reserves 4
- **THEN** `data.reservation` carries `guest_cpus` 4, `reserved_cpus` 4, `reservable_cpus` 17 and
  `fits` true
- **AND** the read passes.

#### Scenario: The guests exceed the reservation

- **WHEN** `ethos host status --guest-cpus 12` runs on a host of 18 CPUs that reserves 4
- **THEN** the read answers `block` with `host_reservation_exceeded`
- **AND** `data.reservation.fits` is false
- **AND** its next action names 12 as the value of `reserved_cpus` to declare.

#### Scenario: No reservation holds the guests

- **WHEN** `ethos host status --guest-cpus 20` runs on a host of 18 CPUs
- **THEN** the read answers `block` with `host_reservation_exceeded`
- **AND** its next action names the guests' sizes as the repair: 17 virtual CPUs or fewer in total
- **AND** it names no value to declare.

#### Scenario: No count is given

- **WHEN** `ethos host status` runs without `--guest-cpus`
- **THEN** the result carries no `data.reservation`.

#### Scenario: The count is negative

- **WHEN** `--guest-cpus` is below zero
- **THEN** the read answers `block` with `host_reservation_invalid`.

## ADDED Requirements

### Requirement: A run's work directory carries its owner's mark

`ethos host run --work <name>` SHALL create `build/runtime/work/<name>/` in the repository and,
before the run queues, mark it with the actor that the run declared, its operation and the time.
A directory SHALL keep its first mark. A run SHALL be refused with `host_work_owned:<name>` when
the directory carries another owner's mark or one that cannot be read. A run that declares no
actor SHALL write no mark.

#### Scenario: A run names its work directory

- **WHEN** `ethos host run --work render -- <command>` runs with a declared actor
- **THEN** `build/runtime/work/render/.ethos-owner.json` names that actor, the operation
  `host.run` and the time
- **AND** the command finds the mark when it starts.

#### Scenario: The same owner runs again

- **WHEN** a later run of the same actor names the same directory
- **THEN** it runs
- **AND** the mark is unchanged.

#### Scenario: Another owner holds the directory

- **WHEN** the directory carries another actor's mark, or a mark that cannot be read
- **THEN** the run is refused with `host_work_owned:render`
- **AND** its command does not run, it takes no ticket, and the mark is unchanged.

#### Scenario: The run declares no actor

- **WHEN** a run without a declared actor names a directory that carries no mark
- **THEN** it runs and writes no mark, so the directory's owner stays unknown
- **AND** the same run in a marked directory is refused with `host_work_owned:render`.

#### Scenario: The name is not one directory

- **WHEN** `--work` names a path, a parent directory or a name that is not lowercase
- **THEN** the run is refused with `host_work_invalid`
- **AND** nothing is created.

#### Scenario: The work home cannot be written

- **WHEN** the directory or its mark cannot be created
- **THEN** the run is refused with `host_work_unavailable`
- **AND** its command does not run.

### Requirement: A ticket holder's test scratch carries its owner's mark

The Python behavior probe SHALL mark the scratch root of one attempt with the owner record of a
work directory when its process holds or has joined a host ticket and declares an actor. The mark
SHALL end with the scratch. A run outside the queue, or one that declares no actor, SHALL write no
mark, and a mark that cannot be written SHALL NOT fail the attempt.

#### Scenario: A proof under a ticket runs its tests

- **WHEN** the behavior probe makes its scratch root while its process holds a host ticket
- **THEN** `.ethos-owner.json` in that root names the declared actor and the provider
  `provider.python-behavior` while the tests run
- **AND** the mark is removed with the scratch when the attempt ends.

#### Scenario: The probe runs outside the queue

- **WHEN** the behavior probe runs with no host ticket in its environment
- **THEN** its scratch root carries no mark.

#### Scenario: The holder declares no actor

- **WHEN** the behavior probe runs under a ticket whose holder declared no actor
- **THEN** its scratch root carries no mark, and its owner stays unknown.
