## ADDED Requirements

### Requirement: The per-test bound detects hangs

The Python test gate SHALL bound each test by one declared hang limit, set well above the slowest healthy test's duration inside a full proof at the admitted host load. A test MAY declare a shorter limit to time one specific operation. No test SHALL declare a limit at or above the declared one.

#### Scenario: A heavy test runs inside a busy full proof

- **WHEN** a test that takes 51 s alone takes 123 s inside a full proof at the admitted host load
- **THEN** its own assertions decide its result, not the hang limit

#### Scenario: A test stops making progress

- **WHEN** a test makes no progress
- **THEN** it fails at the declared limit and reports its stack

#### Scenario: A test raises its own limit

- **WHEN** a test declares a limit at or above the declared one, or a limit that is not a literal
- **THEN** the architecture regression fails
