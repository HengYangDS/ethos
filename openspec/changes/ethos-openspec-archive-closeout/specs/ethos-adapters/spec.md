## MODIFIED Requirements

### Requirement: Official OpenSpec Lifecycle Adapter

ETHOS SHALL compose official OpenSpec CLI output with ETHOS lifecycle carrier
review.

#### Scenario: Archive closeout gaps block land and closeout

- **GIVEN** official OpenSpec list status has no completed active changes
- **AND** an archived change is missing archive metadata or has incomplete tasks
- **WHEN** ETHOS evaluates OpenSpec lifecycle closeout for land or accepted-root
  closeout
- **THEN** ETHOS reports the archive issue as a required gap
- **AND** land or closeout remains blocked until archive state is repaired.
