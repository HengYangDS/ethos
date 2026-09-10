## ADDED Requirements

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
- **THEN** its dependent and transitive dependents are blocked without execution
- **AND** independent diagnostics may complete

### Requirement: Inexpensive source failures precede heavy verification

The sole gate registry SHALL declare lint, schema, configuration, type and source
budget readiness before the heavy test gate. Public proof and local CI SHALL
consume that same dependency closure without a parallel phase registry.

#### Scenario: A cheap source-readiness check fails

- **WHEN** a declared prerequisite of the test gate is failed or unknown
- **THEN** test execution, coverage consumption and dependent package delivery do not run
- **AND** the result names the failed prerequisite instead of fabricating test failures

#### Scenario: All source-readiness checks pass

- **WHEN** the requested graph is valid and its readiness prerequisites pass
- **THEN** all selected tests and existing coverage and delivery obligations remain required
- **AND** dry-run still projects unknown rather than claiming executed success
