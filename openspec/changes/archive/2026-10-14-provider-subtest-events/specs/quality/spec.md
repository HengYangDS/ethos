## ADDED Requirements

### Requirement: Provider behavior evidence counts native subtests

The product Python behavior provider SHALL capture pytest's report-log events with its JUnit and coverage reports, and SHALL validate JUnit totals against those events, so passing subtests that JUnit counts but does not emit are explained rather than rejected.

#### Scenario: A test passes its subtests

- **WHEN** the locked pytest run passes a test with subtests
- **THEN** the behavior evidence verifies
- **AND** its test total counts each subtest

#### Scenario: The event report is missing

- **WHEN** pytest writes JUnit but no event report
- **THEN** the behavior evidence blocks as `test_event_report_missing`

### Requirement: Provider coverage binds every committed Python subject

The product Python behavior provider SHALL bind each file in its coverage report to a committed Python subject of the repository, and SHALL require coverage only of product source subjects, so tests that execute committed tooling do not block the behavior evidence.

#### Scenario: A test executes committed tooling

- **WHEN** a passing test executes a committed Python file whose role is tooling
- **THEN** the behavior evidence verifies

### Requirement: Provider static analysis uses the shared line width

The product Python static provider SHALL run Ruff isolated from repository configuration with a line length of 100 columns, the shared formatter width of governed repositories.

#### Scenario: A line reaches the shared width

- **WHEN** an authored Python line is 100 columns long
- **THEN** the static evidence does not report `E501` for it

#### Scenario: A line exceeds the shared width

- **WHEN** an authored Python line is 101 columns long
- **THEN** the static evidence blocks with `E501`
