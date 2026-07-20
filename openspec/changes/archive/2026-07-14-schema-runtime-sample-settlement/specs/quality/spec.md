## ADDED Requirements

### Requirement: Runtime-Owned Schema Contract Validation

ETHOS SHALL validate published schemas and real repository producer payloads
without retaining synthetic sample builders in production runtime merely to
exercise schema shape.

#### Scenario: UI projection fields remain rejected

- **WHEN** a workspace-status producer test adds a forbidden UI projection field
  to its real payload
- **THEN** validation SHALL fail with required gaps
- **AND THEN** the validation SHALL remain owned by that producer boundary.
