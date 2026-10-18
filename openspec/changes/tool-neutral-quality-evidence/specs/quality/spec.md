## MODIFIED Requirements

### Requirement: Declared native outputs bind one gate attempt

A gate MAY declare `native_outputs` naming each report its native command writes, with its
producing session and a format: `junit-xml`, `cobertura-xml`, `lcov`, `sarif`, or an optional
Python producer report (`nox-json`, `pytest-jsonl`, `python-runtime-json`). ETHOS SHALL capture
them from one owned attempt for the gate's verification providers. Missing, duplicate, malformed or
session-inconsistent outputs SHALL NOT satisfy the gate.

#### Scenario: An adopter profile declares native reports

- **WHEN** a profile or gate registry declares valid native outputs for a gate
- **THEN** the declaration validates against the published gate schema
- **AND** the verification provider receives the reports of that exact attempt

#### Scenario: A declared report is absent or inconsistent

- **WHEN** a declared report is missing, duplicated, malformed or bound to another session
- **THEN** the gate cannot pass and reports the exact native output gap

#### Scenario: A gate declares no Nox report

- **WHEN** a gate declares JUnit, coverage and SARIF outputs without a Nox report
- **THEN** the declaration validates and its reports are judged from that attempt alone

#### Scenario: A gate declares a Nox report

- **WHEN** a gate declares one Nox report
- **THEN** its command writes that report to the declared path
- **AND** every declared output names a session of that report, and each such session succeeded

#### Scenario: A removed format is declared

- **WHEN** a declaration names `coverage-xml` or `ruff-json`
- **THEN** validation refuses it before any execution

## ADDED Requirements

### Requirement: Native quality evidence is judged by property

A verification provider SHALL judge declared native reports by property, not producer. Behavior
passes only when every JUnit report has a test case and no failure or error, and each applicable
file a Cobertura or LCOV report measures was executed. Static analysis passes only when SARIF has
no warning or error and its inventory lists each file it covers. A provider SHALL claim only the
files its evidence covers.

#### Scenario: Tests pass and the measured files ran

- **WHEN** every JUnit report passes and coverage shows each measured applicable file executed
- **THEN** behavior passes and claims exactly those files

#### Scenario: A measured file never ran

- **WHEN** coverage measures an applicable file with executable lines and none of them ran
- **THEN** behavior blocks for that file

#### Scenario: A test failed or none ran

- **WHEN** a JUnit report has a failure or error, or contains no test case
- **THEN** behavior blocks

#### Scenario: SARIF reports a finding

- **WHEN** a SARIF result is a warning or an error
- **THEN** static analysis blocks with that result
- **AND** a note alone does not block

#### Scenario: SARIF scope is unknown

- **WHEN** a SARIF run does not list its analyzed artifacts and no declared same-session Python
  runtime recorded the files its checker read
- **THEN** static analysis blocks because its scope is unknown

#### Scenario: Evidence covers some applicable files

- **WHEN** a native report covers only some applicable files
- **THEN** the provider claims only those files
- **AND** the quality obligation stays unproven until other admitted evidence covers the rest

#### Scenario: A gate declares no native outputs

- **WHEN** a quality verifier runs for a gate without native outputs
- **THEN** ETHOS runs its own check for each language it supports
- **AND** files in other languages stay unclaimed instead of blocking that gate
- **AND** a gate whose applicable files are all in such languages blocks
