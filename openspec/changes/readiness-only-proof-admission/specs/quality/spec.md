## MODIFIED Requirements

### Requirement: Readiness gates precede host-load admission

A full executing proof SHALL run its readiness gates, every planned gate that is not a test or
package gate and does not depend on one, before it waits for its repository's proof slot and host
load. When a readiness gate fails, the proof SHALL end without that wait and SHALL NOT run its test
or package gates. When all pass, it SHALL wait once and run each remaining gate once. A full
executing proof that plans only readiness gates SHALL NOT wait for the proof slot or host load.

#### Scenario: A readiness gate fails

- **WHEN** a readiness gate of a full executing proof fails
- **THEN** the proof does not wait for the proof slot or host load
- **AND** each test and package gate reports `gate_dependency_not_proven` without running
- **AND** the proof result keeps the evidence of every readiness gate.

#### Scenario: Every readiness gate passes

- **WHEN** every readiness gate of a full executing proof that plans another gate passes
- **THEN** the proof waits for the slot and host load once, after its last readiness gate
- **AND** runs each test and package gate once, with no readiness gate run again
- **AND** one proof result keeps every gate and the admission it waited for.

#### Scenario: A full proof plans only readiness gates

- **WHEN** a full executing proof plans no gate other than its readiness gates
- **THEN** it runs them without waiting for the proof slot or host load
- **AND** its result records no admission.
