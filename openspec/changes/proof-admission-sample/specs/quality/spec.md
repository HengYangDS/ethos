## MODIFIED Requirements

### Requirement: Full proofs and nested work share the host admission

A full executing proof SHALL take its repository slot, then the host slot, then wait until two
consecutive 1-minute load samples fall within the limit; its bound SHALL NOT run behind a live
holder of the host slot. A sample that the proof took before its readiness gates SHALL count as
the first of the two only when it fell within the limit, is at least one sampling interval old,
and the proof then took both slots without waiting. An executing host proof SHALL run its
readiness gates without waiting and SHALL hold the host slot, with no repository slot and no load
wait, while its other gates run. Work under a live admission SHALL join it, and a token whose
holder has exited SHALL admit nothing.

#### Scenario: Work runs under a live admission

- **WHEN** a command that `ethos host run` admitted starts a proof or another admitted command
- **THEN** that work joins the live admission and does not wait for itself
- **AND** a copied token whose holder has exited admits nothing.

#### Scenario: Load dips once between busy phases

- **WHEN** one 1-minute load sample falls within the limit and the next does not
- **THEN** the proof keeps waiting until two consecutive samples fall within it.

#### Scenario: A quiet host admits a proof after its readiness gates

- **GIVEN** a load sample within the limit that the proof took before its readiness gates, and
  readiness gates that ran for at least one sampling interval
- **WHEN** both slots are free and the sample at admission falls within the limit
- **THEN** the proof is admitted without a further wait.

#### Scenario: An earlier sample does not replace a second look

- **WHEN** the earlier sample was above the limit, could not be taken, or is younger than one
  sampling interval, or the proof waited for a slot, or the sample at admission is above the limit
- **THEN** the proof waits until two consecutive samples at admission fall within the limit.

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
