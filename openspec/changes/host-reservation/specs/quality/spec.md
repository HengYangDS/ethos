## MODIFIED Requirements

### Requirement: Heavy local work is admitted host-wide

ETHOS SHALL admit heavy local work through one host-wide queue beside each repository's proof
slot. At most the declared number of slots SHALL run at a time, in arrival order, and a holder's
exit SHALL free its place without cleanup. The wait SHALL be bounded; a waiter's event and the gap
that ends the wait SHALL name the holder's operation, process and start time. A holder record SHALL
NOT contain command arguments, and a result SHALL NOT print a holder's repository path.

#### Scenario: Two heavy runs share a host

- **GIVEN** a host that declares one slot
- **WHEN** two heavy runs ask for admission
- **THEN** the later waits until the earlier ends
- **AND** a third runs after both, in arrival order.

#### Scenario: A holder dies

- **WHEN** the process holding a place in the queue exits without releasing it
- **THEN** the next waiter is admitted without any cleanup by age.

#### Scenario: The wait reaches its bound

- **WHEN** a heavy run waits for the whole admission bound
- **THEN** it ends without running, with `host_admission_contended:<operation>:<pid>:<since>` of
  the earliest live holder
- **AND** its next action is `ethos host status --json`
- **AND** the result holds no path of the holder's repository.

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
admitted work SHALL receive a worker cap of the CPUs that the declaration leaves, at least one.
The cap SHALL keep a smaller positive worker count that the caller's environment already declares.

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

- **GIVEN** an environment that sets `PYTEST_XDIST_AUTO_NUM_WORKERS` to 4 on a host whose
  declaration leaves 8 CPUs
- **WHEN** work is admitted
- **THEN** its children receive 4 workers
- **AND** `ETHOS_HOST_CPU_CAP` carries 8.

### Requirement: Full proofs and nested work share the host admission

A full executing proof SHALL take its repository slot, then the host slot, then wait until two
consecutive 1-minute load samples fall within the limit. An executing host proof SHALL run its
readiness gates without waiting and SHALL hold the host slot, with no repository slot and no load
wait, while its other gates run. Work that runs under a live admission SHALL join it instead of
being admitted again, and a token whose holder has exited SHALL admit nothing.

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

#### Scenario: A host proof waits for the whole bound

- **WHEN** the host slot stays held for the whole admission bound
- **THEN** the host proof runs no test or package gate
- **AND** it answers `block` with `host_admission_contended` and exits 1.

#### Scenario: The host root cannot be written

- **WHEN** an executing host proof cannot write its ticket under the host root
- **THEN** it answers `block` with `host_admission_unavailable` and exits 1.

## ADDED Requirements

### Requirement: One read lists the host queue and its holder

`ethos host status` SHALL be a catalog read that returns this host's declaration, its 1-minute load
and every live ticket in arrival order with its state, operation, executable, owner mark, process
and start time. The owner mark SHALL be the actor that the holder itself declared, or empty. The
read SHALL print no repository path, SHALL say only whether a ticket belongs to the reading
repository, and SHALL remove nothing from the queue.

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

- **WHEN** a ticket's holder exited without leaving
- **THEN** the read does not list it
- **AND** the read removes no file; the next waiter removes the ticket.

#### Scenario: The declaration is invalid

- **WHEN** `host.toml` is unreadable or out of range
- **THEN** the read answers `block` with the declaration's gap.

### Requirement: The guests' CPUs are checked against the reservation

Given the guests' virtual CPU count, `ethos host status` SHALL report whether it fits inside the
declared `reserved_cpus`, and SHALL answer `block` with `host_reservation_exceeded` when it does
not. The count SHALL come from the request, whose caller reads it from the guests' own
configuration; ETHOS SHALL read no hypervisor.

#### Scenario: The guests fit

- **WHEN** `ethos host status --guest-cpus 4` runs on a host that reserves 4 CPUs
- **THEN** `data.reservation` carries `guest_cpus` 4, `reserved_cpus` 4 and `fits` true
- **AND** the read passes.

#### Scenario: The guests exceed the reservation

- **WHEN** `ethos host status --guest-cpus 8` runs on a host that reserves 4 CPUs
- **THEN** the read answers `block` with `host_reservation_exceeded`
- **AND** `data.reservation.fits` is false.

#### Scenario: No count is given

- **WHEN** `ethos host status` runs without `--guest-cpus`
- **THEN** the result carries no `data.reservation`.

#### Scenario: The count is negative

- **WHEN** `--guest-cpus` is below zero
- **THEN** the read answers `block` with `host_reservation_invalid`.
