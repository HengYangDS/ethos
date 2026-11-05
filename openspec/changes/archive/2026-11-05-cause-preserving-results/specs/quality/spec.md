## MODIFIED Requirements

### Requirement: Quality Execution Closure

The declared quality graph SHALL select and execute each required obligation once for the requested
evidence plane. Local CI and repository proof SHALL reuse the same gate identities, dependency
closure and shared runner rather than maintain independent membership or scheduling state. Offline
source correctness, online freshness, package verification and hosted observation SHALL remain
distinguishable; an unobserved external property SHALL NOT be reported as a passing local property.

#### Scenario: The same quality plane is invoked from two entrypoints

- **WHEN** local CI and repository proof evaluate the same source and requested quality plane
- **THEN** their required gate identities and dependency closure agree
- **AND** each required check executes at most once through its existing owner
- **AND** the result identifies checks outside that evidence plane without silently dropping
  obligations or claiming hosted success

#### Scenario: A prerequisite did not pass

- **WHEN** execution is requested and a gate has a failed, unknown or unexecuted prerequisite
- **THEN** the shared runner does not execute that dependent gate
- **AND** its result is unknown when an unmet prerequisite is unknown and blocked otherwise,
  and identifies the unmet prerequisite
- **AND** independent diagnostic checks may continue within the declared budget

#### Scenario: Coverage fails before package delivery

- **WHEN** the required Python test result, whose execution decides the coverage floor, is not
  passing
- **THEN** dependent package creation and installation do not execute
- **AND** no success receipt is emitted for the incomplete quality closure

#### Scenario: External observation is unavailable

- **WHEN** a requested online freshness or hosted-observation check cannot obtain its declared
  evidence
- **THEN** the result records unknown or blocked with an actionable cause
- **AND** offline source correctness is neither relabeled as external assurance nor made dependent
  on an undeclared remote

#### Scenario: Readiness is not executed proof

- **WHEN** the graph is projected without execution
- **THEN** all planned results remain unknown with no exit code
- **AND** unmet execution prerequisites are not reported as observed failures

#### Scenario: Fallback evidence must describe the tested source

- **WHEN** local CI is requested against uncommitted source or an invalid selection
- **THEN** it records a non-passing preflight result without executing the closure
- **AND** changes to HEAD, working bytes or policy during execution invalidate the result

#### Scenario: Execution evidence is incomplete or interrupted

- **WHEN** execution is interrupted or has missing, duplicate, mismatched or unsuccessful results
- **THEN** the fallback receipt cannot report success
- **AND** a non-passing record exists before execution and records incomplete observation

### Requirement: Dependency-ready execution without unrelated barriers

The shared runner SHALL execute each admitted gate at most once when its actual
prerequisites have completed, without awaiting unrelated readers. It SHALL
respect bounded capacity, exclusive writers, deterministic result order and
failed-dependency blocking. Scheduler state SHALL be transient.

#### Scenario: A ready child has an unrelated slow peer

- **WHEN** one prerequisite finishes while an unrelated reader remains active
- **THEN** its ready child can use free capacity before that reader finishes
- **AND** returned evidence order is independent of completion order

#### Scenario: A writer becomes ready

- **WHEN** a declared writing gate is ready while readers are active
- **THEN** the runner drains active readers before executing the writer alone
- **AND** no new check overlaps that writer

#### Scenario: An invalid plan is supplied

- **WHEN** the graph has a cycle, missing dependency, duplicate node or invalid capacity
- **THEN** validation rejects it before any check executes

#### Scenario: A dependency fails or remains unknown

- **WHEN** a prerequisite does not return pass with exit code zero
- **THEN** its dependent and transitive dependents do not execute
- **AND** each of them is unknown when an unmet prerequisite is unknown, and blocked otherwise
- **AND** independent diagnostics may complete

### Requirement: Every gate runs under a recorded deadline

Each gate SHALL run under a deadline: its declared `timeout_seconds`, which SHALL stay within the
`timeout` group's bound, otherwise the repository's `timeout.gate_seconds`. A command inside a gate
SHALL run within that deadline. A proof SHALL record each gate's effective timeout with its source,
and every repository value looser than its default with the stated reason.

#### Scenario: An undeclared gate runs too long

- **WHEN** a gate without its own timeout runs longer than the repository's `timeout.gate_seconds`
- **THEN** it reports `gate_timeout:<gate>` with verdict unknown, the timeout, its source and
  the elapsed time

#### Scenario: A command inside a gate hangs

- **WHEN** a command inside a gate does not finish
- **THEN** the gate's deadline ends it, and the gate reports `gate_timeout:<gate>` as unknown

#### Scenario: A gate declares a timeout beyond the bound

- **WHEN** a gate declares `timeout_seconds` above the `timeout.gate_seconds` bound
- **THEN** the repository profile reports the gate, and no proof runs it.

#### Scenario: A repository loosens a value

- **WHEN** a binding declares a higher value with a reason
- **THEN** the proof summary lists the parameter, its value, its default and the reason.
