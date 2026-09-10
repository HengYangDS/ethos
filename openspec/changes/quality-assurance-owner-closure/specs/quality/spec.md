## ADDED Requirements

### Requirement: Quality Execution Closure

The declared quality graph SHALL select and execute each required obligation
once for the requested evidence plane. Local CI and repository proof SHALL
reuse the same gate identities, dependency closure and shared runner rather
than maintain independent membership or scheduling state. Offline source
correctness, online freshness, package verification and hosted observation
SHALL remain distinguishable; an unobserved external property SHALL NOT be
reported as a passing local property.

#### Scenario: The same quality plane is invoked from two entrypoints

- **WHEN** local CI and repository proof evaluate the same source and requested
  quality plane
- **THEN** their required gate identities and dependency closure agree
- **AND** each required check executes at most once through its existing owner
- **AND** the result identifies checks outside that evidence plane without
  silently dropping obligations or claiming hosted success

#### Scenario: A prerequisite did not pass

- **WHEN** execution is requested and a gate has a failed, unknown or unexecuted prerequisite
- **THEN** the shared runner does not execute that dependent gate
- **AND** its result is blocked and identifies the unmet prerequisite
- **AND** independent diagnostic checks may continue within the declared budget

#### Scenario: Coverage fails before package delivery

- **WHEN** the required coverage-floor result is not passing
- **THEN** dependent package creation and installation do not execute
- **AND** no success receipt is emitted for the incomplete quality closure

#### Scenario: External observation is unavailable

- **WHEN** a requested online freshness or hosted-observation check cannot
  obtain its declared evidence
- **THEN** the result records unknown or blocked with an actionable cause
- **AND** offline source correctness is neither relabeled as external assurance
  nor made dependent on an undeclared remote


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
