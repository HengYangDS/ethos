## ADDED Requirements

### Requirement: A coverage shortfall names itself

When every test of the Python behavior gate passes but the combined coverage that the same
execution measured is below the floor of the repository's coverage carrier, the gate SHALL block
with `quality_behavior_coverage_below_floor` and record the floor beside the measurement. It SHALL
decide the floor as coverage.py does, and a failing test SHALL still report
`quality_behavior_tests_failed`.

#### Scenario: Tests pass below the floor

- **WHEN** every test passes and the measured coverage rounds below the declared floor
- **THEN** the gate blocks with `quality_behavior_coverage_below_floor`
- **AND** its coverage evidence names the floor and its precision

#### Scenario: A test fails

- **WHEN** a test fails, whatever the coverage
- **THEN** the gate blocks with `quality_behavior_tests_failed`
