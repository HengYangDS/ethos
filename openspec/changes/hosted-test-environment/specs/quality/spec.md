## MODIFIED Requirements

### Requirement: Hosted verification owns its native test prerequisites

Hosted verification SHALL prepare each native executable required by its tests through the existing
version-bound installer before executing the test gate. Preparation SHALL belong to the invoking
process, not another job. A failed prerequisite SHALL prevent test execution, retain its diagnostic
and remove stale proof and test outputs without weakening assertions or increasing concurrency. The
tests SHALL find each prepared executable among their locked tools.

#### Scenario: Another job has prepared the scanner

- **WHEN** a clean verify job runs native scanner regressions after a separate secrets job passed
- **THEN** verify prepares the declared scanner in its own execution environment
- **AND** the unchanged real scanner assertions execute with that supply

#### Scenario: A required executable cannot be prepared

- **WHEN** either scanner or budget-tool preparation fails
- **THEN** proof does not execute and the supply failure is reported
- **AND** previous passing proof and test artifacts cannot be reused

#### Scenario: The shipped probe runs the tests

- **WHEN** hosted verification has prepared gitleaks through ETHOS's native supply and mise has not
  installed it
- **THEN** the probe's tests find that gitleaks after mise's own installs and before the host
  command baseline
- **AND** a repository whose native supply ETHOS has not prepared gets the same environment as
  before

### Requirement: The per-test bound detects hangs

The Python test gate SHALL bound each test by one declared hang limit, set well above the slowest
healthy test's duration inside a full proof at the admitted host load. A test MAY declare a shorter
limit to time one specific operation. No test SHALL declare a limit at or above the declared one.
Every thread's stack SHALL reach the run's log before the limit ends a test's process.

#### Scenario: A heavy test runs inside a busy full proof

- **WHEN** a test that takes 51 s alone takes 123 s inside a full proof at the admitted host load
- **THEN** its own assertions decide its result, not the hang limit

#### Scenario: A test stops making progress

- **WHEN** a test makes no progress
- **THEN** it fails at the declared limit and reports its stack

#### Scenario: A test raises its own limit

- **WHEN** a test declares a limit at or above the declared one, or a limit that is not a literal
- **THEN** the architecture regression fails

#### Scenario: A Windows worker makes no progress

- **WHEN** a test makes no progress inside a pytest-xdist worker on Windows, where the limit ends
  the worker process
- **THEN** every thread's stack is in the job log before the worker ends
