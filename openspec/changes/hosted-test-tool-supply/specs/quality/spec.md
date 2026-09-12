## ADDED Requirements

### Requirement: Hosted verification owns its native test prerequisites

Hosted verification SHALL prepare each native executable required by its tests
through the existing version-bound installer before executing the test gate.
Preparation SHALL belong to the invoking process, not another job. A failed
prerequisite SHALL prevent test execution, retain its diagnostic and remove stale
proof and test outputs without weakening assertions or increasing concurrency.

#### Scenario: Another job has prepared the scanner

- **WHEN** a clean verify job runs native scanner regressions after a separate
  secrets job passed
- **THEN** verify prepares the declared scanner in its own execution environment
- **AND** the unchanged real scanner assertions execute with that supply

#### Scenario: A required executable cannot be prepared

- **WHEN** either scanner or budget-tool preparation fails
- **THEN** proof does not execute and the supply failure is reported
- **AND** previous passing proof and test artifacts cannot be reused
