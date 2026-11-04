## ADDED Requirements

### Requirement: Heavy local work is admitted host-wide

ETHOS SHALL admit heavy local work through one host-wide queue beside each repository's proof slot. At most the declared number of slots SHALL run at a time, in arrival order, and a holder's exit SHALL free its place without cleanup. The wait SHALL be bounded, and the gap that ends it SHALL name the holder's repository, executable and start time. A holder record SHALL NOT contain command arguments.

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
- **THEN** it ends without running, with a gap that names the holder's repository, executable and
  start time.

### Requirement: The host declaration bounds admitted work

The host declaration SHALL be the only host-wide authority for the slot count, the reserved CPUs and the load limit. A value out of range SHALL be refused with a named gap and not clamped, and admitted work SHALL receive a worker cap of the CPUs that the declaration leaves, at least one.

#### Scenario: The host declaration is out of range

- **WHEN** `host.toml` declares zero slots, reserves every CPU or declares a load limit that is not positive
- **THEN** admission refuses with a named gap and does not clamp the value.

#### Scenario: Busy guests hold the host's load

- **GIVEN** CI virtual machines that keep the host's load above half its CPUs
- **WHEN** `host.toml` declares a higher `load_limit`
- **THEN** a full proof admits under that limit, and a wait that reaches its bound names the load, the limit and where the limit came from.

### Requirement: Full proofs and nested work share the host admission

A full executing proof SHALL take its repository slot, then the host slot, then wait until two consecutive 1-minute load samples fall within the limit. Work that runs under a live admission SHALL join it instead of being admitted again, and a token whose holder has exited SHALL admit nothing.

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
