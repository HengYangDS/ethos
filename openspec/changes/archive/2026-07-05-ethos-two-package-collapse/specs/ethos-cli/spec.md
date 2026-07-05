## MODIFIED Requirements

### Requirement: Two-Package Runtime Surface

ETHOS CLI SHALL compose runtime adapters, repository governance, assistant projection, and testing helpers from the `ethos` package.

#### Scenario: Runtime packages collapse into ethos

- **WHEN** CLI and runtime imports are inspected after migration
- **THEN** adapters, assistants, repository, and testing modules resolve under `ethos`
- **AND** retired package roots do not remain as public compatibility modules.
