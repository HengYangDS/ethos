## ADDED Requirements

### Requirement: Zero-Tolerance Python Type Policy

ETHOS SHALL enforce Python type checking as a fail-closed, zero-diagnostic
quality gate for every package declared by `.config/checks/ty/policy.toml`.
The policy SHALL contain no type-diagnostic ratchet, baseline, ignore, or
exception once a package is governed by this requirement.

#### Scenario: Unknown type-tool execution blocks proof

- **WHEN** `ty` is unavailable, cannot launch, exits without a terminal
  diagnostic result, or produces malformed terminal output
- **THEN** `ethos quality types --json` reports a stable required execution gap
- **AND** the command exits non-zero through its enforced quality verdict
- **AND** the result does not report the unknown execution as zero diagnostics

#### Scenario: Every declared package has zero diagnostics

- **WHEN** `ethos quality types --json` runs with an available `ty` runtime
- **THEN** every package declared in the zero-tolerance policy reports
  `tier = "zero_tolerance"` and `limit = 0`
- **AND** any positive diagnostic count reports
  `ty_zero_tolerance_violation:<package>:<count>`
- **AND** CI and the default proof graph invoke the same owner gate

#### Scenario: Retired type debt cannot return as a baseline

- **WHEN** all governed packages report zero diagnostics
- **THEN** the type policy contains no ratchet table or equivalent exception
- **AND** a future diagnostic blocks immediately rather than establishing a
  new tolerated count
