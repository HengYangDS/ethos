## ADDED Requirements

### Requirement: Independent test work is distributable

The Python test owner SHALL use native item-level work stealing for parallel
execution without changing selected tests, worker limits, isolation or coverage
requirements. Serial execution SHALL remain supported.

#### Scenario: One module contains the longest independent test scope

- **WHEN** multiple workers execute independent test items in that module
- **THEN** the scheduler can distribute its pending items across workers
- **AND** the collected test identities and required outcomes remain unchanged

### Requirement: Hosted test feedback is visible and source bound

Both hosted projections SHALL publish test-owned JUnit and coverage artifacts,
including outputs available after failure. GitLab SHALL declare native test and
coverage reports. GitHub SHALL expose a native job summary with the exact source,
proof outcome and available test observations. Reporting SHALL NOT mint proof,
hide failed execution or fabricate successful missing observations.

#### Scenario: A hosted test fails

- **WHEN** a test run produces failing JUnit results
- **THEN** available reports remain uploaded and inspectable
- **AND** the hosted job retains its non-passing execution result

#### Scenario: Test observations are unavailable

- **WHEN** JUnit or coverage output is missing or malformed
- **THEN** the summary explicitly identifies unavailable observations
- **AND** it does not substitute zero tests or a passing coverage result
