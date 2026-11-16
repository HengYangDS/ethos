## ADDED Requirements

### Requirement: Suite legs repeat the test suite once for a release

A batch-head dispatch and the drift schedule SHALL repeat the Python test suite, through the
shipped behavior probe and within the test gate's deadline, on Linux x64 at Python 3.12 and 3.13
and on Windows x64 at Python 3.14. With the quality gates job on Linux arm64 and the local proof
on macOS arm64, each operating system, both architectures and each supported Python version then
run the suite once for a release. The Linux legs SHALL be required; the Windows leg MAY fail.

#### Scenario: A batch head is qualified

- **WHEN** a dispatch names the head it qualifies and runs at that commit
- **THEN** the suite runs on Linux x64 at Python 3.12 and at 3.13 and on Windows x64 at Python 3.14
- **AND** each leg runs the tests on the interpreter of its own Python version
- **AND** each leg uploads its JUnit and coverage reports whether its tests pass or fail

#### Scenario: A push or pull request runs no suite leg

- **WHEN** `dev` or a proposal ref is pushed, or a pull request is opened or updated
- **THEN** no suite leg runs

#### Scenario: The Windows leg fails

- **WHEN** the Windows x64 leg fails while every required job succeeds
- **THEN** the leg fails by its declared tolerance
- **AND** the run does not fail

#### Scenario: The test gate's deadline bounds a leg

- **WHEN** a suite leg is projected
- **THEN** it passes the timeout that the test gate declares to the probe as the suite's deadline
- **AND** the leg's environment sync and its suite share that one deadline
- **AND** a suite job class whose timeout does not exceed that timeout by the declared margin for
  the leg's supply steps does not compile

### Requirement: A suite leg records coverage and decides no floor

A suite leg SHALL run the tests on the interpreter that started it, also where the repository
locks another one, and never on another. It SHALL measure coverage without applying the coverage
carrier's floor. It SHALL block on a failed test, an unexercised product file or an incomplete
coverage scope, never with `quality_behavior_coverage_below_floor`. The floor SHALL be decided once
for a proof attempt, by its test gate; a gate SHALL NOT run the probe as a leg.

#### Scenario: A leg measures less than the floor

- **WHEN** every test of a leg passes and its measured coverage rounds below the declared floor
- **THEN** the leg passes
- **AND** its coverage evidence holds the measurement and names no floor

#### Scenario: A leg's run fails

- **WHEN** a leg's test run fails, whatever its coverage
- **THEN** the leg blocks with `quality_behavior_tests_failed`

#### Scenario: The repository locks another interpreter

- **WHEN** a leg starts on Python 3.12 in a repository whose locked interpreter is Python 3.14
- **THEN** the tests run on Python 3.12

#### Scenario: The project does not admit the leg's interpreter

- **WHEN** a leg starts on an interpreter outside the project's Python range
- **THEN** the leg blocks with `quality_behavior_test_environment_sync_failed`
- **AND** no test runs on another interpreter

#### Scenario: A proof attempt decides the floor

- **WHEN** a default or full proof runs its test gate, on a workstation or in the quality gates job
- **THEN** that one execution runs on the locked interpreter and decides the floor
- **AND** no suite leg's measurement is read for it

## MODIFIED Requirements

### Requirement: One aggregate check reports the per-push jobs

GitHub's projection SHALL carry one aggregate job, `hosted checks`, that needs every required job
of a commit run, commit-range admission and the required suite legs included, and runs whatever
their results. It SHALL pass only when each needed job succeeded where its event runs it and was
skipped only where its event has no such job. It SHALL NOT need a job that may fail: the external
link observation or the Windows suite leg. Its result is a host observation, not repository proof.

#### Scenario: A per-push job fails

- **WHEN** commit-range admission, a host conformance leg or the quality gates job fails or is
  cancelled
- **THEN** `hosted checks` fails

#### Scenario: A job is skipped on a commit run

- **WHEN** a push of `dev` or a proposal ref, or a pull request, ends with commit-range admission,
  host conformance or the quality gates job skipped
- **THEN** `hosted checks` fails

#### Scenario: An event has no such job

- **WHEN** `main` follows `dev` and its admission succeeds, or a batch-head dispatch or the drift
  schedule ends with every commit-scoped job successful
- **THEN** `hosted checks` succeeds with the jobs that the event does not have skipped

#### Scenario: A push has no suite leg

- **WHEN** a push or a pull request ends with its per-push jobs successful and the suite legs
  skipped
- **THEN** `hosted checks` succeeds

#### Scenario: A required suite leg fails

- **WHEN** a batch-head dispatch or the drift schedule ends with the Linux x64 leg at Python 3.12
  or at 3.13 failed, cancelled or skipped
- **THEN** `hosted checks` fails

#### Scenario: The external link observation fails

- **WHEN** external link health finds an unreachable or redirecting link while every required
  per-push job succeeds
- **THEN** its job keeps its report and fails by its declared tolerance without failing the run
- **AND** `hosted checks`, which neither needs that job nor reads its result, succeeds

#### Scenario: The Windows suite leg fails

- **WHEN** the Windows x64 suite leg fails while every required job succeeds
- **THEN** `hosted checks`, which neither needs that leg nor reads its result, succeeds
