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
